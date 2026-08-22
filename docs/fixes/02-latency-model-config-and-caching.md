# Fix — Latency: FPL API Caching & Connection Reuse

## Context (updated)

Earlier investigation into 80-100s turn latency initially flagged an `LLM_MODEL`/`GROQ_MODEL_NAME`
mismatch as a likely contributor. That turned out to be based on an outdated copy of the codebase —
**the multi-provider work is already fully and correctly implemented**: `settings.py` has proper
`LLM_PROVIDER`/`LLM_MODEL`/`OPENAI_API_KEY` fields, `helpers.py` correctly dispatches to `ChatGroq`
or `ChatOpenAI`, and `gpt-5.6-luna` is a real, current OpenAI model (released July 2026 as the
fast/cost-efficient tier of the GPT-5.6 family) — not a typo or a silently-ignored setting. No fix
needed there. This guide now covers only the confirmed, still-outstanding issue: the FPL API
client layer.

## The actual issue

`FPLOfficialAPIClient` has zero caching and creates a brand-new `httpx.AsyncClient` (fresh
TCP+TLS handshake) on every instantiation:

```python
class FPLOfficialAPIClient:
    def __init__(self):
        self.base_url = settings.FPL_API_BASE_URL
        self.session = AsyncClient()
```

This constructor is called fresh at 12+ call sites across `tools/fpl.py`, `tools/user.py`, and
`graph/nodes.py::context_injection_node` — once per tool call, not once per turn. Nearly every
method in `fpl_data.py`/`team_data.py` starts with `await self.api.get_bootstrap_data()`, which
hits `/bootstrap-static/` fresh every time — a multi-MB response containing every player, team,
and gameweek event, identical for every user, re-fetched and re-parsed from scratch on every call
that needs it. A single turn calling two or three tools that each need player/team data can easily
mean two or three full bootstrap-static downloads over brand-new connections. This is the primary
suspected driver of the 80-100s turns, independent of which LLM provider is in use.

## Fix — shared HTTP client + TTL cache for shared/global data only

### Scope — what gets cached, what doesn't

Cache **only** genuinely shared, slow-changing data: `/bootstrap-static/` and `/fixtures/`. Both
are identical for every user and change at most a handful of times a day.

**Do not** cache per-manager endpoints (`get_manager_data`, `get_gameweek_picks`,
`get_manager_history`, `get_transfer_data`, `get_classic_league_standings`) — these are
user-specific and time-sensitive. Caching those would serve stale personal data, which is a
correctness bug, not a latency win.

### 1. `settings.py` additions

```python
    # FPL API client settings
    FPL_API_TIMEOUT_SECONDS: float = 10.0
    FPL_BOOTSTRAP_CACHE_TTL_SECONDS: int = 300  # 5 minutes
    FPL_FIXTURES_CACHE_TTL_SECONDS: int = 300
```

### 2. `modules/fpl/fpl_api.py` (full replacement)

```python
import asyncio
from typing import Dict, Optional

import httpx
from cachetools import TTLCache

from fpl_gaffer.core.exceptions import FPLAPIError
from fpl_gaffer.settings import settings

# ----- Shared HTTP client -----
# A single pooled client for the whole process, instead of a fresh TCP+TLS handshake on every
# FPLOfficialAPIClient() instantiation (there are 12+ call sites across tools/graph nodes).
_shared_client: Optional[httpx.AsyncClient] = None
_client_init_lock = asyncio.Lock()


async def get_shared_http_client() -> httpx.AsyncClient:
    """Get (or lazily create) the shared httpx.AsyncClient used by every FPLOfficialAPIClient
    instance that doesn't have an explicit session injected. Connections are pooled/reused across
    calls instead of opening a new one every time."""
    global _shared_client
    if _shared_client is not None:
        return _shared_client
    async with _client_init_lock:
        if _shared_client is None:
            _shared_client = httpx.AsyncClient(
                timeout=settings.FPL_API_TIMEOUT_SECONDS,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
    return _shared_client


async def close_shared_http_client() -> None:
    """Call on app shutdown to close the pooled connections cleanly."""
    global _shared_client
    if _shared_client is not None:
        await _shared_client.aclose()
        _shared_client = None


# ----- Shared, process-wide TTL caches for global (non-user-specific) FPL data -----
_bootstrap_cache: TTLCache = TTLCache(maxsize=1, ttl=settings.FPL_BOOTSTRAP_CACHE_TTL_SECONDS)
_bootstrap_lock = asyncio.Lock()

_fixtures_cache: TTLCache = TTLCache(maxsize=1, ttl=settings.FPL_FIXTURES_CACHE_TTL_SECONDS)
_fixtures_lock = asyncio.Lock()


class FPLOfficialAPIClient:
    def __init__(self, session: Optional[httpx.AsyncClient] = None):
        self.base_url = settings.FPL_API_BASE_URL
        # Explicit session mainly for tests/scripts that want an isolated client. Production call
        # sites (all 12+ of them) pass nothing and transparently share one pooled client.
        self._session = session

    async def _get_session(self) -> httpx.AsyncClient:
        if self._session is not None:
            return self._session
        return await get_shared_http_client()

    async def get_bootstrap_data(self) -> Dict:
        """Get basic FPL data including gameweeks, teams, players, chips. Cached for
        FPL_BOOTSTRAP_CACHE_TTL_SECONDS - this endpoint is identical for every user and changes
        at most a few times a day, and it's called from nearly every tool, so caching it is the
        single highest-leverage latency fix in this client."""
        if "data" in _bootstrap_cache:
            return _bootstrap_cache["data"]
        async with _bootstrap_lock:
            # Double-checked: another concurrent call may have populated it while we waited.
            if "data" in _bootstrap_cache:
                return _bootstrap_cache["data"]
            data = await self._get("/bootstrap-static/")
            _bootstrap_cache["data"] = data
            return data

    async def get_fixtures(self) -> Dict:
        """Get fixtures for the season. Cached the same way and for the same reason as
        get_bootstrap_data - shared across all users, slow-changing."""
        if "data" in _fixtures_cache:
            return _fixtures_cache["data"]
        async with _fixtures_lock:
            if "data" in _fixtures_cache:
                return _fixtures_cache["data"]
            data = await self._get("/fixtures/")
            _fixtures_cache["data"] = data
            return data

    async def get_player_summary(self, player_id: int) -> Dict:
        """Get a single player's fixtures, this-season gameweek history, and past seasons."""
        return await self._get(f"/element-summary/{player_id}/")

    async def get_manager_data(self, manager_id: int) -> Dict:
        """Get basic manager data from the FPL API. NOT cached - changes with live points."""
        return await self._get(f"/entry/{manager_id}/")

    async def get_gameweek_picks(self, manager_id: int, gw: int) -> Dict:
        """Get the picks for a specific gameweek. NOT cached - user-specific."""
        return await self._get(f"/entry/{manager_id}/event/{gw}/picks/")

    async def get_manager_history(self, manager_id: int) -> Dict:
        """Get a manager's history data. NOT cached - user-specific."""
        return await self._get(f"/entry/{manager_id}/history/")

    async def get_transfer_data(self, manager_id: int):
        """Get a manager's transfer data. NOT cached - changes with live transfers."""
        return await self._get(f"/entry/{manager_id}/transfers/")

    async def get_classic_league_standings(self, league_id: int, page: int = 1):
        """Get the standings for a league. NOT cached - changes with live points."""
        params = {"page_standings": page}
        return await self._get(f"/leagues-classic/{league_id}/standings/", params=params)

    async def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Internal GET requests handler."""
        try:
            session = await self._get_session()
            response = await session.get(f"{self.base_url}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise FPLAPIError(f"Failed to fetch endpoint '{endpoint}': {e}") from e

    # ----- Context manager support -----
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # No-op: the underlying session is either shared (owned/closed elsewhere) or explicitly
        # injected by the caller, so this client never owns a session's lifecycle itself. Note
        # this is a behavior change from before - the old __aexit__ called self.session.aclose(),
        # which would be wrong now that the session is usually the shared, pooled one used by
        # every other in-flight request.
        return None
```

This is a drop-in replacement — every existing call site (`FPLOfficialAPIClient()` with no args)
keeps working unchanged, and transparently starts sharing one pooled connection and hitting the
cache instead of the network for bootstrap/fixtures.

### 3. Close the shared client on app shutdown

In `integrations/api/main.py`'s `lifespan` (alongside the checkpointer close, if that's already
wired from the deployment guide):

```python
from fpl_gaffer.modules.fpl.fpl_api import close_shared_http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_compiled_graph()
    yield
    await close_shared_http_client()
    await close_graph()
```

### 4. `pyproject.toml`

`cachetools` and `httpx` are already dependencies — no change needed there.

## Sanity checklist

- [ ] `pytest` still passes — `test_user_tools.py`, `test_tool_error_isolation.py` mock
      `FPLTeamDataManger`/data-manager classes directly, so this change shouldn't affect them, but
      confirm rather than assume.
- [ ] Add one new test: call `get_bootstrap_data()` twice in a row with the underlying `_get`
      mocked, and assert the mock was only invoked once (proves the cache is actually
      short-circuiting, not just present in the code).
- [ ] Add a second test confirming two `FPLOfficialAPIClient()` instances created without an
      explicit session share the same underlying `httpx.AsyncClient` (via `get_shared_http_client()`
      returning the same object both times) — proves connection reuse is actually happening, not
      just structurally possible.
- [ ] Manually run a turn that triggers 2-3 tools (e.g. "compare Haaland and Watkins and check
      what the scouts think") and compare wall-clock latency before/after this change. This is the
      number that actually matters.
- [ ] Confirm `__aexit__` is not called anywhere expecting the old close-on-exit behavior — grep
      `async with FPLOfficialAPIClient()` across the codebase; if any call site relies on that
      pattern to clean up a per-call session, it now no-ops by design (the session is shared), which
      is correct but worth confirming nothing assumed otherwise.

## If latency is still high after this

Two things worth checking next, in order — but only after measuring with the fix above in place,
not before:

1. **A/B the LLM provider directly**, since multi-provider switching already works: flip `.env` to
   `LLM_PROVIDER=groq` and rerun the same turn, compare wall-clock time against `openai`/
   `gpt-5.6-luna`. This tells you directly how much of any remaining latency is provider-side.
2. **Check reasoning-effort/verbosity defaults for GPT-5.6 on the Responses API.** If staying on
   OpenAI, GPT-5-series models typically support a `reasoning_effort`/`verbosity`-style parameter
   in the Responses API; if `helpers.py`'s `ChatOpenAI(...)` call isn't setting it explicitly, it
   may default to something higher than needed for a WhatsApp-conversational-latency use case, even
   on the Luna tier.

Response validation node timing and tool-call batching (the original #3/#4 from the first pass of
this investigation) are still on the table if needed, but confirm with real before/after numbers
first — this fix and the two checks above are much more likely to explain the bulk of it.
