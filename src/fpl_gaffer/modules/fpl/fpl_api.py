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
