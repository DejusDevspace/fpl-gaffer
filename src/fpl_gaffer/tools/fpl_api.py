import httpx
from typing import Dict


class FPLOfficialAPI:
    def __init__(self):
        self.base_url = "https://fantasy.premierleague.com/api"
        self.session = httpx.AsyncClient()

    async def get_bootstrap_data(self) -> Dict:
        """Get basic FPL data including gameweeks, teams, players, chips..."""
        try:
            response = await self.session.get("{}/boostrap-static/".format(self.base_url))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print("Error fetching bootstrap data: {}".format(e))
            return {}

    async def get_gameweek_data(self) -> Dict:
        """Get info for the current gameweek and deadline."""
        bootstrap_data = self.get_bootstrap_data()
        if not bootstrap_data:
            return {}

        # Get current gameweek from bootstrap data
        current_gw = None
        for gw in bootstrap_data.get("events", []):
            if gw["is_current"]:
                current_gw = gw
                break

        # Get fixtures for the current gameweek
        fixtures = await self.get_fixtures()
        if not fixtures:
            return {}

        # Filter fixtures for the current gameweek
        current_gw_fixtures = [
            fixture for fixture in fixtures if fixture.get("event") == current_gw.get("id")
        ] if current_gw else []

        return {
            "gameweek": current_gw.get("id") if current_gw else None,
            "deadline": current_gw.get("deadline_time") if current_gw else None,
            "finished": current_gw.get("finished") if current_gw else False,
            "fixtures": current_gw_fixtures
        }

    async def get_fixtures(self) -> Dict:
        """Get fixtures for the season."""
        try:
            response = await self.session.get("{}/fixtures/".format(self.base_url))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print("Error fetching fixtures: {}".format(e))
            return {}
