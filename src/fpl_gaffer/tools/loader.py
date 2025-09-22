import inspect
import asyncio
from typing import List, Callable, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
from langchain.tools import Tool, BaseTool
from fpl_gaffer.core.exceptions import ToolExecutionError
from fpl_gaffer.tools.news import news_search_tool, NewsSearchInput
from fpl_gaffer.tools.user import get_user_team_info_tool, UserTeamInfoInput
from fpl_gaffer.tools.fpl import (
    PlayerDataInput, PlayerByPositionInput, get_players_by_position_tool, get_player_data_tool,
    FixturesForRangeInput, get_fixtures_for_range_tool
)


class AsyncFPLTool(BaseTool):
    """Custom async tool wrapper to handle async execution in LangGraph context."""
    func: Callable
    input_schema: BaseModel = None

    # Allow custom types
    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _arun(self, **kwargs) -> Any:
        """Async execution of the tool."""
        try:
            return await self.func(**kwargs)
        except Exception as e:
            raise ToolExecutionError(
                f"Error executing tool '{self.name}': {e}"
            ) from e

    def _run(self, **kwargs) -> Any:
        """Fallback sync wrapper."""
        try:
            return asyncio.run(self.func(**kwargs))
        except Exception as e:
            raise ToolExecutionError(
                f"Error executing tool '{self.name}': {e}"
            ) from e


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

def create_tools() -> List[AsyncFPLTool]:
    """Create and return a list of tools for the FPL Gaffer."""
    return [
        AsyncFPLTool(
            name="news_search_tool",
            description="Search for FPL news, expert analysis, injury updates, press conference information, etc."
                        "Use this when you need information about player/team news, injury, expert opinions, or "
                        "general FPL updates.",
            func=news_search_tool,
            args_schema=NewsSearchInput
        ),
        AsyncFPLTool(
            name="get_user_team_info_tool",
            description="Get comprehensive information about a user's FPL team including squad, transfers, "
                        "and finances. Use this when you need information about the user's team, players, or "
                        "financial situation.",
            func=get_user_team_info_tool,
            args_schema=UserTeamInfoInput
        ),
        AsyncFPLTool(
            name="get_players_by_position_tool",
            description="Get players by position and max price. Use this when you need information for player "
                        "replacements or transfer suggestions based on position and budget. Use position short forms "
                        "like GKP, DEF, MID, FWD.000",
            func=get_players_by_position_tool,
            args_schema=PlayerByPositionInput
        ),
        AsyncFPLTool(
            name="get_player_data_tool",
            description="Get detailed player data including stats, form, and injuries. Use this when you need "
                        "information about specific players.",
            func=get_player_data_tool,
            args_schema=PlayerDataInput
        ),
        AsyncFPLTool(
            name="get_fixtures_for_range_tool",
            description="Get fixtures from the current gameweek to the next x gameweeks. Use this when you need "
                        "information about upcoming fixtures or planning for future gameweeks.",
            func=get_fixtures_for_range_tool,
            args_schema=FixturesForRangeInput
        )
    ]

def get_tool_prompt_description(tools: List[AsyncFPLTool]) -> str:
    """Return a formatted string describing all tools and their args."""
    lines = []
    for i, tool in enumerate(tools, 1):
        # Collect argument name: type pairs from the Pydantic model
        if tool.args_schema and issubclass(tool.args_schema, BaseModel):
            fields = [
                f"{name}: {field.annotation.__name__}"
                for name, field in tool.args_schema.model_fields.items()
            ]
            args = ", ".join(fields) if fields else "none"
        else:
            args = "none"
        # Build the line with name, args, and description
        lines.append(
            f"  {i}. {tool.name}: args {{{{{args}}}}}\n     {tool.description}"
        )
    return "\n".join(lines)

# Create tools and their descriptions at module load time
TOOLS: List[AsyncFPLTool] = create_tools()
TOOLS_DESCRIPTION = get_tool_prompt_description(TOOLS)
