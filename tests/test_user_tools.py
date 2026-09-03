import unittest
from unittest.mock import AsyncMock, Mock, patch

from fpl_gaffer.tools.fpl import get_players_by_position
from fpl_gaffer.tools.news import news_search
from fpl_gaffer.tools.user import get_user_team_info


class UserToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_user_team_tool_uses_last_available_picks_gameweek(self):
        team_manager = Mock()
        team_manager.extract_team_data = AsyncMock(return_value={"manager_id": 123})

        with patch(
            "fpl_gaffer.tools.user.FPLTeamDataManger",
            return_value=team_manager,
        ) as manager_cls:
            result = await get_user_team_info(manager_id=123, gameweek=5)

        manager_cls.assert_called_once()
        _, manager_id, picks_gameweek = manager_cls.call_args.args
        self.assertEqual(manager_id, 123)
        self.assertEqual(picks_gameweek, 5)
        self.assertEqual(result, {"manager_id": 123})

    async def test_user_team_tool_never_requests_gameweek_zero(self):
        team_manager = Mock()
        team_manager.extract_team_data = AsyncMock(return_value={"manager_id": 123})

        with patch(
            "fpl_gaffer.tools.user.FPLTeamDataManger",
            return_value=team_manager,
        ) as manager_cls:
            await get_user_team_info(manager_id=123, gameweek=1)

        _, _, picks_gameweek = manager_cls.call_args.args
        self.assertEqual(picks_gameweek, 1)

    async def test_user_team_tool_returns_generic_error_no_leak(self):
        """tool_error must return {"error": "unavailable"} and never leak the
        raw exception message into the result."""
        team_manager = Mock()
        team_manager.extract_team_data = AsyncMock(
            side_effect=RuntimeError("secret endpoint /api/v2/picks returned 503")
        )

        with patch(
            "fpl_gaffer.tools.user.FPLTeamDataManger",
            return_value=team_manager,
        ):
            result = await get_user_team_info(manager_id=123, gameweek=5)

        self.assertEqual(result, {"error": "unavailable"})
        self.assertNotIn("503", str(result))
        self.assertNotIn("secret", str(result))


class FPLToolErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_fpl_tool_returns_generic_error_no_leak(self):
        """get_players_by_position must not leak exception details."""
        from unittest.mock import MagicMock

        with patch("fpl_gaffer.tools.fpl.FPLDataManager") as mock_dm_cls:
            mock_dm = MagicMock()
            mock_dm.get_players_by_position = AsyncMock(
                side_effect=ConnectionError("GET https://fantasy.premierleague.com/api/foo 502")
            )
            mock_dm_cls.return_value = mock_dm

            result = await get_players_by_position("MID", 10.0)

        self.assertEqual(result, {"error": "unavailable"})
        self.assertNotIn("502", str(result))
        self.assertNotIn("fantasy.premierleague.com", str(result))


class NewsToolErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_news_tool_returns_generic_error_no_leak(self):
        """news_search must not leak exception details."""
        with patch("fpl_gaffer.tools.news.FPLNewsSearchClient") as mock_cls:
            mock_client = Mock()
            mock_client.search_news = AsyncMock(side_effect=RuntimeError("Tavily API key invalid: tvly-xxx"))
            mock_cls.return_value = mock_client

            result = await news_search("test query")

        self.assertEqual(result, {"error": "unavailable"})
        self.assertNotIn("tvly-xxx", str(result))
        self.assertNotIn("Tavily", str(result))


if __name__ == "__main__":
    unittest.main()
