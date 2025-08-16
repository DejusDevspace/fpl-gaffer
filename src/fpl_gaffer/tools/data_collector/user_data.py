from fpl_gaffer.settings import settings
from httpx import AsyncClient
from typing import Dict, Optional
from fpl_gaffer.core.exceptions import FPLAPIError
from datetime import datetime

class FPLUserDataExtractor:
    def __init__(self):
        self.base_url = settings.fpl_api_base_url
        self.session = AsyncClient()

    async def extract_user_data(self, manager_id: int) -> Dict:
        """Get user data from the FPL API."""
        # Get manager data
        manager_data = await self.get_manager_data(manager_id)
        if not manager_data:
            return {}

        # Build user profile
        user_profile = self.build_user_profile(manager_data)

        return user_profile

    async def get_manager_data(self, manager_id: int) -> Dict:
        """Get basic manager data from the FPL API."""
        try:
            response = await self.session.get(f"{self.base_url}/entry/{manager_id}/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise FPLAPIError(
                f"Failed to fetch manager data for manager with ID: {manager_id}:\n {e}"
            ) from e

    def build_user_profile(self, manager_data: Dict) -> Dict:
        """Build a user profile from extracted data."""
        if not manager_data:
            return {}

        # Add manager data to user profile
        user_profile = {
            "manager_id": manager_data.get("id"),
            "team_name": manager_data.get("name"),
            "first_name": manager_data.get("player_first_name"),
            "last_name": manager_data.get("player_last_name"),
            "region": manager_data.get("player_region_name"),
            "overall_rank": manager_data.get("summary_overall_rank"),
            "total_points": manager_data.get("summary_overall_points"),
            "last_updated": datetime.now().isoformat()
        }

        return user_profile