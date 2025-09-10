from typing import Dict
from pydantic import BaseModel, Field
from fpl_gaffer.modules import FPLNewsSearchClient
from fpl_gaffer.core.exceptions import ToolError


class NewsSearchInput(BaseModel):
    """Input schema for the news search tool."""
    query: str = Field(..., description="The search query for news search.")


async def search_news_tool(query: str) -> Dict:
    """Search FPL-related news, expert analysis, scout tips, injury news, etc."""
    news_client = FPLNewsSearchClient()

    try:
        results = await news_client.search_news(query)
        return results
    except Exception as e:
        raise ToolError(f"Error while using news search tool: {e}") from e
