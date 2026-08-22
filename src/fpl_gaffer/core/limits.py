from typing import Dict

from fpl_gaffer.integrations.api.app.services.database import database_service
from fpl_gaffer.settings import settings

DEFAULT_LIMITS: Dict = {
    "max_tool_calls_per_turn": settings.MAX_TOOL_CALLS_PER_TURN,
    "max_context_tokens_before_summary": settings.MAX_CONTEXT_TOKENS_BEFORE_SUMMARY,
    "reasoning_effort": "medium",
}


async def resolve_limits(user_id: str) -> Dict:
    """Resolve the limits that apply to this user's turn, based on their subscription tier.
    Falls back to the 'free' tier's limits if the user can't be resolved for any reason - fail
    closed (most restrictive), not open."""
    try:
        tier = await database_service.get_user_tier(str(user_id))
    except Exception:
        tier = "free"

    tier_config = settings.TIER_LIMITS.get(tier, settings.TIER_LIMITS["free"])

    return {
        "max_tool_calls_per_turn": tier_config["max_tool_calls_per_turn"],
        "max_context_tokens_before_summary": settings.MAX_CONTEXT_TOKENS_BEFORE_SUMMARY,
        "reasoning_effort": tier_config["reasoning_effort"],
        "tier": tier,
        "daily_turn_limit": tier_config["daily_turn_limit"],
    }
