from httpx import AsyncClient
from typing import Dict
from fpl_gaffer.settings import settings
from fpl_gaffer.core.exceptions import FPLAPIError


class FPLOfficialAPI:
    def __init__(self):
        self.base_url = settings.fpl_api_base_url
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

    async def _get(self, endpoint: str) -> Dict:
        """Internal GET requests handler."""
        try:
            response = await self.session.get(f"{self.base_url}{endpoint}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise FPLAPIError(f"Failed to fetch endpoint '{endpoint}': {e}") from e

    # ----- Context manager support ----- #
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()
