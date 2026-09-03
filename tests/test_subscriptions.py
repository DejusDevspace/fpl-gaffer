import unittest
from unittest.mock import AsyncMock, patch

from fpl_gaffer.core.limits import resolve_limits
from fpl_gaffer.integrations.api.app.services.agent_wrapper import agent_wrapper
from fpl_gaffer.settings import settings


class SubscriptionTierLimitsTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_limits_returns_free_tier_for_missing_or_inactive_user(self):
        """When database_service.get_user_tier returns 'free', resolve_limits should return free tier limits."""
        with patch(
            "fpl_gaffer.core.limits.database_service.get_user_tier",
            new_callable=AsyncMock,
            return_value="free",
        ):
            limits = await resolve_limits("user-free-1")

        self.assertEqual(limits["tier"], "free")
        self.assertEqual(limits["daily_turn_limit"], settings.TIER_LIMITS["free"]["daily_turn_limit"])
        self.assertEqual(
            limits["max_tool_calls_per_turn"], settings.TIER_LIMITS["free"]["max_tool_calls_per_turn"]
        )
        self.assertEqual(limits["reasoning_effort"], "low")

    async def test_resolve_limits_returns_basic_tier(self):
        """When user has an active basic subscription, resolve_limits should return basic tier limits."""
        with patch(
            "fpl_gaffer.core.limits.database_service.get_user_tier",
            new_callable=AsyncMock,
            return_value="basic",
        ):
            limits = await resolve_limits("user-basic-1")

        self.assertEqual(limits["tier"], "basic")
        self.assertEqual(limits["daily_turn_limit"], 10)
        self.assertEqual(limits["max_tool_calls_per_turn"], 6)
        self.assertEqual(limits["reasoning_effort"], "medium")

    async def test_resolve_limits_returns_pro_tier(self):
        """When user has an active pro subscription, resolve_limits should return pro tier limits."""
        with patch(
            "fpl_gaffer.core.limits.database_service.get_user_tier",
            new_callable=AsyncMock,
            return_value="pro",
        ):
            limits = await resolve_limits("user-pro-1")

        self.assertEqual(limits["tier"], "pro")
        self.assertEqual(limits["daily_turn_limit"], 20)
        self.assertEqual(limits["max_tool_calls_per_turn"], 10)
        self.assertEqual(limits["reasoning_effort"], "high")

    async def test_resolve_limits_fails_closed_to_free_on_database_error(self):
        """If database_service raises an exception, resolve_limits should fail closed to 'free' tier."""
        with patch(
            "fpl_gaffer.core.limits.database_service.get_user_tier",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Database connection down"),
        ):
            limits = await resolve_limits("user-err-1")

        self.assertEqual(limits["tier"], "free")
        self.assertEqual(limits["daily_turn_limit"], settings.TIER_LIMITS["free"]["daily_turn_limit"])

    async def test_agent_wrapper_enforces_daily_turn_limit_without_running_graph(self):
        """When count_turns_today >= daily_turn_limit, agent_wrapper should return status='limit_reached'
        and should NOT invoke the graph."""
        with (
            patch(
                "fpl_gaffer.integrations.api.app.services.agent_wrapper.database_service.get_fpl_id_by_user_id",
                new_callable=AsyncMock,
                return_value=12345,
            ),
            patch(
                "fpl_gaffer.integrations.api.app.services.agent_wrapper.database_service.count_turns_today",
                new_callable=AsyncMock,
                return_value=5,
            ),
            patch(
                "fpl_gaffer.integrations.api.app.services.agent_wrapper.resolve_limits",
                new_callable=AsyncMock,
                return_value={
                    "tier": "free",
                    "daily_turn_limit": 5,
                    "max_tool_calls_per_turn": 3,
                    "reasoning_effort": "low",
                },
            ),
            patch(
                "fpl_gaffer.integrations.api.app.services.agent_wrapper.get_compiled_graph",
                new_callable=AsyncMock,
            ) as mock_get_graph,
        ):
            result = await agent_wrapper.call_agent(
                prompt="Check my team",
                user_id="user-123",
                fpl_id=12345,
            )

        self.assertEqual(result["status"], "limit_reached")
        self.assertIn("daily limit", result["text"])
        mock_get_graph.assert_not_called()


if __name__ == "__main__":
    unittest.main()
