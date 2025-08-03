import httpx
from typing import Dict


class FPLOfficialAPI:
    def __init__(self):
        self.base_url = "https://fantasy.premierleague.com/api"
        self.session = httpx.AsyncClient()

    async def get_bootstrap_data(self) -> Dict:
        """Get basic FPL data including gameweeks, teams, players, chips..."""
        pass