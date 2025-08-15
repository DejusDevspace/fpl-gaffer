from fpl_gaffer.settings import settings
from httpx import AsyncClient
from typing import Dict
from fpl_gaffer.core.exceptions import FPLAPIError

class FPLUserDataExtractor:
    def __init__(self):
        self.base_url = settings.fpl_api_base_url
        self.session = AsyncClient()

    async def extract_user_data(self, manager_id: int) -> Dict:
        """Get user data from the FPL API."""
        pass
