import unittest

from fpl_gaffer.modules.fpl.fpl_data import FPLDataManager
from fpl_gaffer.modules.user.team_data import FPLTeamDataManger
from fpl_gaffer.tools.news import compact_news_results


class _FakeFPLApi:
    def __init__(self, bootstrap_data=None, history_data=None, fixtures=None):
        self.bootstrap_data = bootstrap_data or {}
        self.history_data = history_data or {}
        self.fixtures = fixtures or []
        self.fixtures_calls = 0

    async def get_bootstrap_data(self):
        return self.bootstrap_data

    async def get_fixtures(self):
        self.fixtures_calls += 1
        return self.fixtures

    async def get_manager_history(self, manager_id):
        return self.history_data


def _player(
    player_id,
    web_name,
    position_id,
    team_id,
    now_cost,
    total_points,
    form="0.0",
    selected_by_percent="0.0",
):
    return {
        "id": player_id,
        "first_name": web_name,
        "second_name": "Player",
        "web_name": web_name,
        "element_type": position_id,
        "team": team_id,
        "now_cost": now_cost,
        "status": "a",
        "news": "",
        "chance_of_playing_next_round": None,
        "total_points": total_points,
        "form": form,
        "selected_by_percent": selected_by_percent,
        "minutes": 900,
        "goals_scored": 1,
        "assists": 2,
        "clean_sheets": 3,
        "expected_goal_involvements": "1.2",
        "unused_payload": "should not leak",
    }


def _bootstrap_data(players):
    return {
        "elements": players,
        "teams": [{"id": 1, "name": "Arsenal"}],
        "element_types": [
            {"id": 1, "singular_name_short": "GKP"},
            {"id": 2, "singular_name_short": "DEF"},
            {"id": 3, "singular_name_short": "MID"},
            {"id": 4, "singular_name_short": "FWD"},
        ],
    }


class FPLDtoTests(unittest.IsolatedAsyncioTestCase):
    async def test_gameweek_context_skips_fixture_fetch_when_not_needed(self):
        bootstrap = _bootstrap_data([])
        bootstrap["events"] = [
            {
                "id": 2,
                "is_next": True,
                "deadline_time": "2026-08-01T10:00:00Z",
            }
        ]
        api = _FakeFPLApi(bootstrap)
        manager = FPLDataManager(api)

        result = await manager.get_gameweek_data(include_fixtures=False)

        self.assertEqual(result["gameweek"], 2)
        self.assertIsNone(result["fixtures"])
        self.assertEqual(api.fixtures_calls, 0)

    async def test_players_by_position_returns_capped_compact_sorted_envelope(self):
        players = [_player(i, f"Mid{i}", 3, 1, 50, total_points=i, form=str(i / 10)) for i in range(1, 11)]
        manager = FPLDataManager(_FakeFPLApi(_bootstrap_data(players)))

        result = await manager.get_players_by_position("MID", 10.0)

        self.assertEqual(result["position"], "MID")
        self.assertEqual(result["count"], 8)
        self.assertEqual(result["total_matches"], 10)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["players"][0]["name"], "Mid10")
        self.assertEqual(result["players"][-1]["name"], "Mid3")
        self.assertNotIn("unused_payload", result["players"][0])

    async def test_fixture_range_is_capped_and_includes_difficulty(self):
        bootstrap = _bootstrap_data([])
        bootstrap["events"] = [{"id": 2, "is_next": True, "deadline_time": None}]
        fixtures = [
            {
                "id": gw,
                "event": gw,
                "team_h": 1,
                "team_a": 1,
                "team_h_difficulty": 2,
                "team_a_difficulty": 4,
                "kickoff_time": None,
            }
            for gw in range(2, 9)
        ]
        manager = FPLDataManager(_FakeFPLApi(bootstrap, fixtures=fixtures))

        result = await manager.get_fixtures_for_range(10)

        self.assertEqual(result["from_gameweek"], 2)
        self.assertEqual(result["to_gameweek"], 6)
        self.assertEqual(result["requested_gameweeks"], 10)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["fixtures"]), 5)
        self.assertEqual(result["fixtures"][0]["home_team_difficulty"], 2)

    async def test_player_data_returns_compact_matching_players(self):
        players = [
            _player(1, "Saka", 3, 1, 100, total_points=150),
            _player(2, "Havertz", 4, 1, 85, total_points=120),
        ]
        manager = FPLDataManager(_FakeFPLApi(_bootstrap_data(players)))

        result = await manager.get_player_data(["saka"])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Saka")
        self.assertEqual(result[0]["position"], "MID")
        self.assertEqual(result[0]["price"], 10.0)
        self.assertNotIn("unused_payload", result[0])

    async def test_team_data_does_not_include_full_history_by_default(self):
        manager = FPLTeamDataManger(_FakeFPLApi(), manager_id=123, gameweek=4)
        team_data = {
            "active_chip": None,
            "entry_history": {
                "points": 64,
                "total_points": 400,
                "overall_rank": 100000,
                "value": 1005,
                "event_transfers": 1,
                "event_transfers_cost": 0,
                "bank": 15,
            },
            "picks": [
                {
                    "element": 1,
                    "position": 1,
                    "multiplier": 2,
                    "is_captain": True,
                    "is_vice_captain": False,
                },
                {
                    "element": 2,
                    "position": 12,
                    "multiplier": 0,
                    "is_captain": False,
                    "is_vice_captain": True,
                },
            ],
        }
        players = {
            1: {
                "name": "Bukayo Saka",
                "team_id": 1,
                "position_id": 3,
                "current_price": 10.0,
                "status": "a",
            },
            2: {
                "name": "Kai Havertz",
                "team_id": 1,
                "position_id": 4,
                "current_price": 8.5,
                "status": "a",
            },
        }
        teams = {1: "Arsenal"}
        positions = {3: "MID", 4: "FWD"}

        result = await manager.extract_squad_info(team_data, players, teams, positions)

        self.assertEqual(result["manager_id"], 123)
        self.assertEqual(result["gameweek"], 4)
        self.assertEqual(result["money_itb"], 1.5)
        self.assertEqual(len(result["starting_xi"]), 1)
        self.assertEqual(len(result["bench"]), 1)
        self.assertNotIn("history", result)

    async def test_news_results_are_compact_and_capped(self):
        raw_results = {
            "answer": "Saka trained before the deadline.",
            "results": [
                {
                    "title": f"News {i}",
                    "url": f"https://example.com/{i}",
                    "source": "Example",
                    "published_date": "2026-07-07",
                    "content": "x" * 700,
                    "score": 0.9,
                    "raw_content": "y" * 5000,
                }
                for i in range(5)
            ],
        }

        result = compact_news_results("saka injury", raw_results)

        self.assertEqual(result["query"], "saka injury")
        self.assertEqual(result["count"], 3)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["results"][0]["snippet"]), 500)
        self.assertNotIn("raw_content", result["results"][0])


if __name__ == "__main__":
    unittest.main()
