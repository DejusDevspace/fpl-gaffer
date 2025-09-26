from fpl_gaffer.modules.fpl.fpl_api import FPLOfficialAPIClient
from fpl_gaffer.settings import settings
from httpx import AsyncClient
from typing import Dict


class FPLUserProfileManager:
    def __init__(self, api: FPLOfficialAPIClient, manager_id: int):
        self.base_url = settings.FPL_API_BASE_URL
        self.session = AsyncClient()
        self.api = api
        self.manager_id = manager_id

    async def extract_user_data(self) -> Dict:
        """Get user data from the FPL API."""
        # Get manager data
        manager_data = await self.api.get_manager_data(self.manager_id)

        if manager_data is None:
            return {}

        # Build user profile
        user_profile = self.build_user_profile(manager_data)

        return user_profile

    def build_user_profile(self, manager_data: Dict) -> Dict:
        """Build a user profile from extracted manager data."""
        if manager_data is None:
            return {}

        return {
            "manager_id": self.manager_id,
            "team_name": manager_data.get("name"),
            "first_name": manager_data.get("player_first_name"),
            "last_name": manager_data.get("player_last_name"),
            "region": manager_data.get("player_region_name"),
            "overall_rank": manager_data.get("summary_overall_rank"),
            "total_points": manager_data.get("summary_overall_points"),
        }

    # TODO: Save and retrieve user most recent gameweek scores, transfers, etc.
