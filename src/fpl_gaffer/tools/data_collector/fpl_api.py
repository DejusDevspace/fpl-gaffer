from httpx import AsyncClient
from typing import Dict
from fpl_gaffer.settings import settings
from fpl_gaffer.core.exceptions import FPLAPIError


class FPLOfficialAPI:
    def __init__(
        self,
        base_url: str,
        session: AsyncClient,
        bootstrap_data: Dict
    ):
        self.base_url = base_url
        self.session = session
        self._bootstrap_data = bootstrap_data

    @classmethod
    async def create(cls) -> "FPLOfficialAPI":
        """Create an instance of FPLOfficialAPI with bootstrap data."""
        base_url = settings.fpl_api_base_url
        session = AsyncClient()
        bootstrap_data = await cls.get_bootstrap_data(base_url, session)
        return cls(base_url, session, bootstrap_data)

    @staticmethod
    async def get_bootstrap_data(base_url, session) -> Dict:
        """Get basic FPL data including gameweeks, teams, players, chips..."""
        try:
            response = await session.get("{}/bootstrap-static/".format(base_url))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise FPLAPIError("Failed to fetch bootstrap data: {}".format(e)) from e

    async def get_gameweek_data(self) -> Dict:
        """Get info for the current gameweek and deadline."""
        if not self._bootstrap_data:
            return {}

        # Get current gameweek from bootstrap data
        current_gw = None
        for gw in self._bootstrap_data.get("events", []):
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
            raise FPLAPIError("Failed to fetch fixtures: {}".format(e)) from e
