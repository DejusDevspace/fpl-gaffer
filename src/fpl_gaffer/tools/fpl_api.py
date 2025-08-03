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
        """Get info for the current gameweek and deadline"""
        pass