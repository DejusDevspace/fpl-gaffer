from typing import Dict, Any
from pydantic import BaseModel, Field
from fpl_gaffer.modules import FPLNewsSearchClient
from fpl_gaffer.core.exceptions import ToolError


class NewsSearchInput(BaseModel):
    """Input schema for the news search tool."""
    query: str = Field(..., description="The search query for news search.")


def compact_news_results(query: str, results: Dict[str, Any], limit: int = 3) -> Dict[str, Any]:
    """Return a small news digest suitable for the agent context."""
    compact_results = []
    for result in results.get("results", [])[:limit]:
        compact_results.append({
            "title": result.get("title"),
            "url": result.get("url"),
            "source": result.get("source"),
            "published_date": result.get("published_date"),
            "snippet": (result.get("content") or "")[:500],
            "score": result.get("score"),
        })

    return {
        "query": query,
        "answer": results.get("answer"),
        "results": compact_results,
        "count": len(compact_results),
        "truncated": len(results.get("results", [])) > len(compact_results),
    }


async def news_search_tool(query: str) -> Dict:
    """Search FPL-related news, expert analysis, scout tips, injury news, etc."""
    news_client = FPLNewsSearchClient()

    try:
        results = await news_client.search_news(query)
        return compact_news_results(query, results)
    except Exception as e:
        raise ToolError(f"Error while using news search tool: {e}") from e
