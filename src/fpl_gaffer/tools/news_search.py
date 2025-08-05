import os
from tavily import TavilyClient
from langchain_community.tools.ddg_search import DuckDuckGoSearchRun
from fpl_gaffer.settings import settings
from typing import Optional, List
from langchain.schema import Document


class FPLNewsSearcher:
    # Required env variables for FPL news searcher
    REQUIRED_ENV_VARS = ["TAVILY_API_KEY"]

    def __init__(self):
        self._validate_env_vars()
        self._client: Optional[TavilyClient] = None
        self.news_docs: List[Document] = []

    def _validate_env_vars(self) -> None:
        """Validate that the required environment variables are available."""
        missing_vars = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    @property
    def client(self) -> TavilyClient:
        """Get or create TavilyClient instance (singleton pattern)."""
        if self._client is None:
            self._client = TavilyClient(
                api_key=settings.TAVILY_API_KEY
            )
        return self._client

    async def search_news(self) -> List[Document]:
        """Core function to search for all news."""
        self._search_injury_news()
        self._search_team_news()
        self._search_fpl_news()
        return self.news_docs

    async def _search_injury_news(self):
        """Search for FPL injury news."""
        pass

    async def _search_team_news(self):
        """Search for premier league teams news."""
        pass

    async def _search_fpl_news(self):
        """Search for FPL news and tips."""
        pass
