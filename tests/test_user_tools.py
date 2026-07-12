import unittest
from unittest.mock import AsyncMock, Mock, patch

from fpl_gaffer.tools.user import get_user_team_info_tool


class UserToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_user_team_tool_uses_last_available_picks_gameweek(self):
        team_manager = Mock()
        team_manager.extract_team_data = AsyncMock(return_value={"manager_id": 123})

        with patch(
            "fpl_gaffer.tools.user.FPLTeamDataManger",
            return_value=team_manager,
        ) as manager_cls:
            result = await get_user_team_info_tool(manager_id=123, gameweek=5)

        manager_cls.assert_called_once()
        _, manager_id, picks_gameweek = manager_cls.call_args.args
        self.assertEqual(manager_id, 123)
        self.assertEqual(picks_gameweek, 4)
        self.assertEqual(result, {"manager_id": 123})

    async def test_user_team_tool_never_requests_gameweek_zero(self):
        team_manager = Mock()
        team_manager.extract_team_data = AsyncMock(return_value={"manager_id": 123})

        with patch(
            "fpl_gaffer.tools.user.FPLTeamDataManger",
            return_value=team_manager,
        ) as manager_cls:
            await get_user_team_info_tool(manager_id=123, gameweek=1)

        _, _, picks_gameweek = manager_cls.call_args.args
        self.assertEqual(picks_gameweek, 1)


if __name__ == "__main__":
    unittest.main()
