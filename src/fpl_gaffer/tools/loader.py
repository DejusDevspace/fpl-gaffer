import inspect
import asyncio
from typing import List, Callable, Dict, Any
from pydantic import BaseModel
from langchain.tools import Tool
from fpl_gaffer.core.exceptions import ToolExecutionError
from fpl_gaffer.tools.news import news_search_tool, NewsSearchInput
from fpl_gaffer.tools.user import get_user_team_info_tool, UserTeamInfoInput

# TODO: Investigate sync/async tool execution errors.
def create_tool_wrapper(func: Callable) -> Callable:
    """Return an adaptible callable for sync/async functions for tools."""
    async def async_wrapper(inputs: Dict | BaseModel) -> Any:
        try:
            # Ensure inputs are a plain dict
            if isinstance(inputs, BaseModel):
                inputs = inputs.model_dump()

            # await for async functions
            if inspect.iscoroutinefunction(func):
                return await func(**inputs)

            # Run directly if function is sync
            return func(**inputs)

        except Exception as e:
            raise ToolExecutionError(
                f"Error executing tool function '{func.__name__}': {e}"
            ) from e

    def sync_wrapper(inputs: Dict | BaseModel) -> Any:
        try:
            # Run async_wrapper in a new event loop
            return asyncio.run(async_wrapper(inputs))
        except Exception as e:
            raise ToolExecutionError(
                f"Error executing tool function '{func.__name__}': {e}"
            ) from e

    # Prefer async wrapper if function is async
    # Default to sync wrapper otherwise
    return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

def create_tools() -> List[Tool]:
    """Create and return a list of tools for the FPL Gaffer."""
    tools = [
        Tool(
            name="news_search_tool",
            description="Search for FPL news, expert analysis, injury updates, press conference information, etc."
                        "Use this when users ask about player/team news, injury, expert opinions, or general FPL updates.",
            func=create_tool_wrapper(news_search_tool),
            args_schema=NewsSearchInput
        ),
        Tool(
            name="get_user_team_info_tool",
            description="Get comprehensive information about a user's FPL team including squad, transfers, "
                        "and finances. Use this when the user asks about their team, players, or financial situation.",
            func=create_tool_wrapper(get_user_team_info_tool),
            args_schema=UserTeamInfoInput
        )
    ]
    return tools
