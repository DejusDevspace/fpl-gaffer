import inspect
from typing import List, Callable, Dict, Any
from pydantic import BaseModel
from langchain.tools import Tool
from fpl_gaffer.core.exceptions import ToolExecutionError
from fpl_gaffer.tools.news import search_news_tool,NewsSearchInput
import asyncio

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
            name="search_news_tool",
            description="Search for FPL news, expert analysis, injury updates, press conference information, etc."
                        "Use this when users ask about player/team news, injury, expert opinions, or general FPL updates.",
            func=create_tool_wrapper(search_news_tool),
            args_schema=NewsSearchInput
        )
    ]
    return tools

search_tool = create_tools()[0]
