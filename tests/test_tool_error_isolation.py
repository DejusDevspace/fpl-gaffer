import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class ToolFailureIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_failing_tool_does_not_raise(self):
        """Verify that a tool implementation blowing up returns an error dict
        to the model (layer 1: per-tool try/except) rather than raising and
        crashing the turn."""
        # Patch at the data-manager level so the error happens *inside* the
        # tool's try/except boundary rather than replacing it.
        from fpl_gaffer.tools.fpl import get_players_by_position

        with patch(
            "fpl_gaffer.tools.fpl.FPLDataManager",
        ) as mock_dm_cls:
            mock_dm = MagicMock()
            mock_dm.get_players_by_position = AsyncMock(side_effect=RuntimeError("boom"))
            mock_dm_cls.return_value = mock_dm

            result = await get_players_by_position("MID", 10.0)

        # The tool should have caught the exception and returned an error dict
        # instead of raising.
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)

    async def test_tool_error_returns_string_message(self):
        """The error value should be a human-readable string the model can
        act on, not a traceback or empty dict."""
        from fpl_gaffer.tools.fpl import get_player_data

        with patch(
            "fpl_gaffer.tools.fpl.FPLDataManager",
        ) as mock_dm_cls:
            mock_dm = MagicMock()
            mock_dm.get_player_data = AsyncMock(side_effect=ValueError("player not found"))
            mock_dm_cls.return_value = mock_dm

            result = await get_player_data(["Nonexistent Player"])

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIsInstance(result["error"], str)
        self.assertTrue(len(result["error"]) > 0)
