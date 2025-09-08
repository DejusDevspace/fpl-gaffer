from fpl_gaffer.modules.fpl.fpl_api import FPLOfficialAPIClient
from fpl_gaffer.utils import build_mappings


class FPLDataManager:
    def __init__(self, api: FPLOfficialAPIClient):
        self.api = api

    async def get_gameweek_data(self):
        """Get info for the current gameweek and deadline."""
        # Fetch bootstrap data
        bootstrap_data = await self.api.get_bootstrap_data()
        if bootstrap_data is None:
            return {}

        # Build team mappings using fpl_mapper
        _, teams, _ = build_mappings(bootstrap_data)

        # Get next gameweek from bootstrap data
        next_gw = next((
            gw for gw in bootstrap_data.get("events", []) if gw["is_next"]
        ), None)

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
                        "kickoff_time": fixture.get("kickoff_time"),
                    })

        return {
            "gameweek": next_gw.get("id") if next_gw else None,
            "deadline": next_gw.get("deadline_time") if next_gw else None,
            # "finished": next_gw.get("finished") if next_gw else False,
            "fixtures": next_gw_fixtures
        }
