from typing import Dict
from pydantic import BaseModel, Field
from fpl_gaffer.modules import FPLNewsSearchClient


class NewsSearchInput(BaseModel):
    """Input schema for the news search tool."""
    query: str = Field(..., description="The search query for news search.")


async def search_news_tool(query: str) -> Dict:
    """Search FPL-related news, expert analysis, scout tips, injury news, etc."""
    news_client = FPLNewsSearchClient()
    results = await news_client.search_news(query)
    return results
