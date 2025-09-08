import os
from tavily import TavilyClient
from fpl_gaffer.settings import settings
from fpl_gaffer.core.exceptions import NewsSearchError
from typing import Optional, List, Dict
from langchain.schema import Document
from langchain_community.document_loaders import UnstructuredURLLoader
from asyncio import to_thread
from dotenv import load_dotenv

#  Load environment variables
_ = load_dotenv()


class FPLNewsSearchClient:
    # Required env variables for FPL news searcher
    REQUIRED_ENV_VARS = ["TAVILY_API_KEY"]

    def __init__(self):
        self._validate_env_vars()
        self._client: Optional[TavilyClient] = None
        self.news_docs: List[Dict] = []

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
        await self._search_injury_news()
        await self._search_team_news()
        await self._search_fpl_news()
        return self.news_docs

    async def _search(self, query: str) -> Dict:
        try:
            return self.client.search(
                query=query,
                search_depth=settings.TAVILY_SEARCH_DEPTH,
                max_results=settings.TAVILY_MAX_SEARCH_RESULTS,
                topic=settings.TAVILY_SEARCH_TOPIC,
                include_raw_content=False
            )
        except Exception as e:
            raise NewsSearchError(
                f"Failed to retrieve search results for query '{query}': {e}"
            ) from e

    async def _search_and_load_docs(self, queries: List[str], category: str = None) -> None:
        """Search for news from queries and loads them into the news documents."""
        for query in queries:
            # Get the tavily api search results for each query
            response = await self._search(query)

            # Add query and category to each result's metadata
            for result in response.get("results", []):
                result["metadata"] = {
                    "source": result.get("url", ""),
                    "title": result.get("title", ""),
                    "query": query,
                    "category": category
                }

            # Get the urls from the search results
            # urls = [result["url"] for result in response.get("results", []) if "url" in result

            # if urls:
            #     try:
            #         # Fetch and parse the content from each URL
            #         loader = UnstructuredURLLoader(urls=urls)
            #         loaded_docs = await to_thread(loader.load)
            #
            #         # Update documents' metadata
            #         for i, d in enumerate(loaded_docs):
            #             d.metadata.update({
            #                 "source": urls[i],
            #                 "query": query,
            #                 "category": category
            #             })
            #
            #         # Extend the news_docs list with the new documents
            #         self.news_docs.extend(loaded_docs)
            #     except Exception as e:
            #         raise NewsSearchError(f"Failed to load documents for query '{query}': {e}") from e

            self.news_docs.extend(response.get("results", []))

    async def _search_injury_news(self) -> None:
        """Search for FPL injury news."""
        await self._search_and_load_docs([
            "Premier League team news injury reports press conference updates",
            "FPL injury doubts and confirmed player absences",
            "Fantasy Premier League player injuries and suspensions"
        ], category="injury")

    async def _search_team_news(self) -> None:
        """Search for premier league teams news."""
        await self._search_and_load_docs([
            "Fantasy Premier League benching risks and squad news",
            "FPL rotation risk players starting XI updates",
        ], category="team")

    async def _search_fpl_news(self) -> None:
        """Search for FPL news and tips."""
        await self._search_and_load_docs([
            "FPL Scout selection and transfer recommendations latest",
            "FPL Scout best tips and advice latest",
            "Fantasy Premier League wildcard and transfer strategy",
            "Fantasy Premier League best transfers this week",
            "FPL captain picks latest expert analysis"
        ], category="fpl")
