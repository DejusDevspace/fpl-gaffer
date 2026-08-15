from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from fpl_gaffer.modules import FPLNewsSearchClient
from fpl_gaffer.settings import settings


class NewsSearchInput(BaseModel):
    query: str = Field(..., description="The search query for general FPL news search.")


class ExpertTipsInput(BaseModel):
    query: str = Field(
        ...,
        description="What to look for expert/scout takes on, e.g. 'gameweek 5 captaincy picks', "
        "'best differentials this week', 'wildcard team ideas'.",
    )


def compact_news_results(query: str, results: Dict[str, Any], limit: int = 3) -> Dict[str, Any]:
    """Return a small news digest suitable for the agent context."""
    compact_results = []
    for result in results.get("results", [])[:limit]:
        compact_results.append(
            {
                "title": result.get("title"),
                "url": result.get("url"),
                "source": result.get("source"),
                "published_date": result.get("published_date"),
                "snippet": (result.get("content") or "")[:500],
                "score": result.get("score"),
            }
        )

    return {
        "query": query,
        "answer": results.get("answer"),
        "results": compact_results,
        "count": len(compact_results),
        "truncated": len(results.get("results", [])) > len(compact_results),
    }


async def news_search(query: str, include_domains: Optional[List[str]] = None) -> Dict:
    """Shared implementation for both news tools. Kept importable for tests."""
    try:
        news_client = FPLNewsSearchClient()
        results = await news_client.search_news(query, include_domains=include_domains)
        return compact_news_results(query, results)
    except Exception as e:
        return {"error": f"Error while searching news: {e}"}


@tool("news_search_tool", args_schema=NewsSearchInput)
async def news_search_tool(query: str) -> Dict:
    """Search general FPL news: injuries, press conferences, transfer news, team announcements.
    Use this for factual/status updates about players or clubs, not for opinion/tip content -
    use get_expert_tips_tool for that instead."""
    return await news_search(query)


@tool("get_expert_tips_tool", args_schema=ExpertTipsInput)
async def get_expert_tips_tool(query: str) -> Dict:
    """Search FPL scout/pundit/community sources specifically (not general news) for tips, picks,
    and consensus opinion - captaincy calls, differential shouts, wildcard/transfer ideas, "scout
    squad" style content. Use this whenever you're forming a suggestion for the user and want to
    ground it in what experienced FPL managers and scouts are currently recommending, in addition
    to (not instead of) the underlying stats tools."""
    return await news_search(query, include_domains=settings.FPL_EXPERT_DOMAINS)
