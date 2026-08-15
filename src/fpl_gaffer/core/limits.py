from typing import Dict

from fpl_gaffer.settings import settings

DEFAULT_LIMITS: Dict = {
    "max_tool_calls_per_turn": settings.MAX_TOOL_CALLS_PER_TURN,
    "max_context_tokens_before_summary": settings.MAX_CONTEXT_TOKENS_BEFORE_SUMMARY,
}


async def resolve_limits(user_id: str) -> Dict:
    """Resolve the limits that apply to this user's turn.

    Currently, this returns one global default for every user (single tier, no subscriptions yet).
    When subscription tiers exist, look up the user's plan here (e.g. via database_service) and
    return per-tier overrides. Nothing else in the graph needs to change when this starts
    returning different values per user - agent_node, response_validation_node, and edges.py all
    read limits from state["limits"], not from settings directly.
    """
    return dict(DEFAULT_LIMITS)
