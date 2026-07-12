from typing import List, Tuple, Dict, Literal
from fpl_gaffer.modules.fpl.fpl_api import FPLOfficialAPIClient
from fpl_gaffer.utils import build_mappings

DEFAULT_PLAYER_RESULT_LIMIT = 8
MAX_FIXTURE_GAMEWEEKS = 5


class FPLDataManager:
    def __init__(self, api: FPLOfficialAPIClient):
        self.api = api

    async def get_gameweek_data(self, include_fixtures: bool = True) -> Dict:
        """Get info for the current gameweek with fixtures and deadline."""
        bootstrap_data, teams, next_gw = await self._fetch_bootstrap_and_next_gw()

        if bootstrap_data is None or next_gw is None:
            return {}

        if not include_fixtures:
            return {
                "gameweek": next_gw.get("id") if next_gw else None,
                "deadline": next_gw.get("deadline_time") if next_gw else None,
                "fixtures": None
            }

        # Get fixtures for the current gameweek
        fixtures = await self.api.get_fixtures()

        if not fixtures:
            return {}

        # Filter fixtures for the next gameweek and convert using team mappings
        next_gw_fixtures = []
        if next_gw:
            for fixture in fixtures:
                if fixture.get("event") == next_gw.get("id"):
                    next_gw_fixtures.append({
                        "id": fixture.get("id"),
                        "home_team": teams.get(fixture.get("team_h"), "Unknown"),
                        "away_team": teams.get(fixture.get("team_a"), "Unknown"),
                        "home_team_difficulty": fixture.get("team_h_difficulty", 0),
                        "away_team_difficulty": fixture.get("team_a_difficulty", 0),
                        "kickoff_time": fixture.get("kickoff_time"),
                    })

        return {
            "gameweek": next_gw.get("id") if next_gw else None,
            "deadline": next_gw.get("deadline_time") if next_gw else None,
            "fixtures": next_gw_fixtures
        }

    async def get_fixtures_for_range(self, num_gameweeks: int = 1) -> Dict:
        """Get fixtures from the current gameweek to the next x gameweeks."""
        bootstrap_data, teams, next_gw = await self._fetch_bootstrap_and_next_gw()

        if bootstrap_data is None or next_gw is None:
            return {}

        # Get fixtures for the next x gameweeks
        all_fixtures = await self.api.get_fixtures()

        if not all_fixtures:
            return {}

        requested_gameweeks = num_gameweeks
        num_gameweeks = max(1, min(num_gameweeks, MAX_FIXTURE_GAMEWEEKS))

        # Get gameweek range
        start_gw = next_gw.get("id")
        target_gws = set(range(start_gw, start_gw + num_gameweeks))

        upcoming_fixtures = []
        for fixture in all_fixtures:
            if fixture.get("event") in target_gws:
                upcoming_fixtures.append({
                    "id": fixture.get("id"),
                    "gameweek": fixture.get("event"),
                    "home_team": teams.get(fixture.get("team_h"), "Unknown"),
                    "away_team": teams.get(fixture.get("team_a"), "Unknown"),
                    "home_team_difficulty": fixture.get("team_h_difficulty"),
                    "away_team_difficulty": fixture.get("team_a_difficulty"),
                    "kickoff_time": fixture.get("kickoff_time"),
                })

        return {
            "from_gameweek": start_gw,
            "to_gameweek": start_gw + num_gameweeks - 1,
            "requested_gameweeks": requested_gameweeks,
            "capped_at_gameweeks": MAX_FIXTURE_GAMEWEEKS,
            "truncated": requested_gameweeks > num_gameweeks,
            "fixtures": upcoming_fixtures
        }

    @staticmethod
    def _compact_player(
        player: Dict,
        teams: Dict,
        positions: Dict,
    ) -> Dict:
        """Return the small player shape the agent needs for reasoning."""
        first_name = player.get("first_name", "")
        second_name = player.get("second_name", "")
        name = player.get("web_name") or f"{first_name} {second_name}".strip()

        return {
            "id": player.get("id"),
            "name": name,
            "position": positions.get(player.get("element_type"), "Unknown"),
            "team": teams.get(player.get("team"), "Unknown"),
            "price": player.get("now_cost", 0) / 10,
            "status": player.get("status"),
            "news": player.get("news") or None,
            "chance_of_playing_next_round": player.get("chance_of_playing_next_round"),
            "total_points": player.get("total_points"),
            "form": player.get("form"),
            "selected_by_percent": player.get("selected_by_percent"),
            "minutes": player.get("minutes"),
            "goals_scored": player.get("goals_scored"),
            "assists": player.get("assists"),
            "clean_sheets": player.get("clean_sheets"),
            "expected_goal_involvements": player.get("expected_goal_involvements"),
        }

    @staticmethod
    def _player_sort_key(player: Dict) -> tuple:
        """Sort transfer candidates by stable, useful launch-time signals."""
        def as_float(value, default: float = 0.0) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        return (
            as_float(player.get("total_points")),
            as_float(player.get("form")),
            as_float(player.get("selected_by_percent")),
            as_float(player.get("minutes")),
        )

    async def get_players_by_position(
        self,
        position: Literal["GKP", "DEF", "MID", "FWD"],
        max_price: float
    ) -> Dict:
        """Get players by position and max price."""
        # Get bootstrap data
        bootstrap_data = await self.api.get_bootstrap_data()

        if bootstrap_data is None:
            return []

        # Build mappings
        players, teams, positions = build_mappings(bootstrap_data)

        # Find position ID from position short name
        position_id = next((
            pid for pid, pname in positions.items() if pname.lower() == position.lower()
        ), None)

        if position_id is None:
            return []

        matched_players = []
        for player in bootstrap_data.get("elements", []):
            if (player.get("element_type") == position_id and
                    (player.get("now_cost", 0) / 10) <= max_price):
                matched_players.append(self._compact_player(player, teams, positions))

        matched_players.sort(key=self._player_sort_key, reverse=True)
        selected_players = matched_players[:DEFAULT_PLAYER_RESULT_LIMIT]

        return {
            "position": position,
            "max_price": max_price,
            "count": len(selected_players),
            "total_matches": len(matched_players),
            "truncated": len(matched_players) > len(selected_players),
            "players": selected_players,
        }

    async def get_player_data(self, player_names: List[str]) -> List[Dict]:
        """Get data for specific player(s) by name."""
        # Get bootstrap data
        bootstrap_data = await self.api.get_bootstrap_data()

        if bootstrap_data is None:
            return []

        _, teams, positions = build_mappings(bootstrap_data)

        # Get all players from bootstrap data
        all_players = bootstrap_data.get("elements", [])
        query_players = [n.lower() for n in player_names]

        matched_players = []
        for player in all_players:
            # Get player names
            first_name = player.get("first_name", "").lower()
            second_name = player.get("second_name", "").lower()
            web_name = player.get("web_name", "").lower()

            for q in query_players:
                # Match if the query appears in any of the name fields
                if (q in first_name) or (q in second_name) or (q in web_name):
                    matched_players.append(self._compact_player(player, teams, positions))
                    break

        return matched_players

    async def _fetch_bootstrap_and_next_gw(self) -> Tuple[Dict, Dict, Dict]:
        """Internal helper to fetch bootstrap data and next gameweek info."""
        # Fetch bootstrap data
        bootstrap_data = await self.api.get_bootstrap_data()

        if bootstrap_data is None:
            return {}, {}, {}

        # Build team mappings using fpl_mapper
        _, teams, _ = build_mappings(bootstrap_data)

        # Get next gameweek from bootstrap data
        next_gw = next((
            gw for gw in bootstrap_data.get("events", []) if gw.get("is_next")
        ), None)

        return bootstrap_data, teams, next_gw
