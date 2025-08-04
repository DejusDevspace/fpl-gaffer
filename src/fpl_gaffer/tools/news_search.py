from langchain_community.tools import TavilySearchResults
from langchain_community.tools.ddg_search import DuckDuckGoSearchRun
from fpl_gaffer.settings import settings


class FPLNewsSearcher:
    def __init__(self):
        tavily_api_key = settings.TAVILY_API_KEY
        if tavily_api_key:
            self.tavily = TavilySearchResults(
                max_results=5,
                search_depth="advanced",
                api_wrapper=tavily_api_key
            )
        else:
            self.tavily = None

        # Alternative search tool using DuckDuckGo (if tavily is not available)
        self.ddg = DuckDuckGoSearchRun()

    async def search_injury_news(self):
        """Search for FPL injury news."""
        pass

    async def search_team_news(self):
        """Search for premier league teams news."""
        pass

    async def search_fpl_news(self):
        """Search for FPL news and tips."""
        pass