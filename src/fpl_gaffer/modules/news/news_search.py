import os
from tavily import TavilyClient
from fpl_gaffer.settings import settings
from fpl_gaffer.core.exceptions import NewsSearchError
from typing import Optional, List, Dict
from langchain.schema import Document
from dotenv import load_dotenv

#  Load environment variables
_ = load_dotenv()


class FPLNewsSearchClient:
    # Required env variables for FPL news searcher
    REQUIRED_ENV_VARS = ["TAVILY_API_KEY"]

    def __init__(self):
        self._validate_env_vars()
        self._client: Optional[TavilyClient] = None

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
        return []

    async def _search(self, query: str) -> Dict:
        try:
            return self.client.search(
                query=query,
                search_depth=settings.TAVILY_SEARCH_DEPTH,
                max_results=settings.TAVILY_MAX_SEARCH_RESULTS,
                topic=settings.TAVILY_SEARCH_TOPIC,
                include_answer=settings.INCLUDE_LLM_SUMMARY,
                include_raw_content=False
            )
        except Exception as e:
            raise NewsSearchError(
                f"Failed to retrieve search results for query '{query}': {e}"
            ) from e

    def search_player_news(self, player_names: List) -> List[Document]:
        """Search news related to specific players."""
        pass

    # TODO: Make below functions dynamic to take in query
    async def _search_injury_news(self) -> None:
        """Search for FPL injury news."""
        pass

    async def _search_team_news(self) -> None:
        """Search for premier league teams news."""
        pass

    async def _search_fpl_news(self) -> None:
        """Search for FPL news and tips."""
        pass
