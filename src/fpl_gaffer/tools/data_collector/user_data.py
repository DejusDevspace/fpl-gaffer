from fpl_gaffer.settings import settings
from httpx import AsyncClient
from typing import Dict, Optional
from fpl_gaffer.core.exceptions import FPLAPIError

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
