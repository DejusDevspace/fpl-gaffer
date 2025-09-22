from typing import List, Tuple, Dict, Literal
from fpl_gaffer.modules.fpl.fpl_api import FPLOfficialAPIClient
from fpl_gaffer.utils import build_mappings


class FPLDataManager:
    def __init__(self, api: FPLOfficialAPIClient):
        self.api = api

    async def get_gameweek_data(self) -> Dict:
        """Get info for the current gameweek and deadline."""
        bootstrap_data, teams, next_gw = await self._fetch_bootstrap_and_next_gw()

        if bootstrap_data is None or next_gw is None:
            return {}

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
            # "fixtures": next_gw_fixtures
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
                    "kickoff_time": fixture.get("kickoff_time"),
                })

        return {
            "from_gameweek": start_gw,
            "to_gameweek": start_gw + num_gameweeks - 1,
            "fixtures": upcoming_fixtures
        }

    # TODO: Get player stats (form, fixtures, injuries, etc.)

    async def get_players_by_position(
        self,
        position: Literal["GKP", "DEF", "MID", "FWD"],
        max_price: float
    ) -> List[Dict]:
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
                matched_players.append(player)

        # TODO: Sort matched players by stat (points, etc), and return top x players.

        return matched_players

    async def get_player_data(self, player_names: List[str]) -> List[Dict]:
        """Get data for specific player(s) by name."""
        # Get bootstrap data
        bootstrap_data = await self.api.get_bootstrap_data()

        if bootstrap_data is None:
            return []

        # Get all players from bootstrap data
        all_players = bootstrap_data.get("elements", [])
        query_players = [n.lower() for n in player_names]

        matched_players = []
        for player in all_players:
            # Get player names
            first_name = player.get("first_name", "").lower()
            second_name = player.get("second_name", "").lower()

            for q in query_players:
                # Match if the query appears in any of the name fields
                if (q in first_name) or (q in second_name):
                    matched_players.append(player)
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
