from httpx import AsyncClient
from typing import Dict, Optional
from fpl_gaffer.settings import settings
from fpl_gaffer.core.exceptions import FPLAPIError


class FPLOfficialAPIClient:
    def __init__(self):
        self.base_url = settings.FPL_API_BASE_URL
        self.session = AsyncClient()

    async def get_bootstrap_data(self) -> Dict:
        """Get basic FPL data including gameweeks, teams, players, chips..."""
        return await self._get("/bootstrap-static/")

    async def get_fixtures(self) -> Dict:
        """Get fixtures for the season."""
        return await self._get("/fixtures/")

    async def get_manager_data(self, manager_id: int) -> Dict:
        """Get basic manager data from the FPL API."""
        return await self._get(f"/entry/{manager_id}/")

    async def get_gameweek_picks(self, manager_id: int, gw: int) -> Dict:
        """Get the picks for a specific gameweek."""
        return await self._get(f"/entry/{manager_id}/event/{gw}/picks/")

    async def get_manager_history(self, manager_id: int) -> Dict:
        """Get a manager's history data."""
        return await self._get(f"/entry/{manager_id}/history/")

    async def get_transfer_data(self, manager_id: int):
        """Get a manager's transfer data."""
        return await self._get(f"/entry/{manager_id}/transfers/")

    async def get_classic_league_standings(self, league_id: int, page: int = 1):
        """Get the standings for a league."""
        params = {"page_standings": page}
        return await self._get(f"/leagues-classic/{league_id}/standings/", params=params)

    async def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Internal GET requests handler."""
        try:
            response = await self.session.get(f"{self.base_url}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise FPLAPIError(f"Failed to fetch endpoint '{endpoint}': {e}") from e

    # ----- Context manager support ----- #
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()
