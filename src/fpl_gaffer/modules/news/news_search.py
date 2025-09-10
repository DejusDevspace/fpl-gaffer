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

    async def search_news(self, query: str) -> Dict:
        """Core function to search for news."""
        results = await self._search(query)

        # TODO: Convert search results to documents?
        return results

    def _create_document_from_result(self, result: Dict) -> Document:
        """Convert a tavily search result dictionary into a langchain Document."""
        pass

    async def _search(self, query: str) -> Dict:
        """Internal search helper."""
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
