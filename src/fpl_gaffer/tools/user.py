import logging
from typing import Dict

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from fpl_gaffer.modules import FPLOfficialAPIClient, FPLTeamDataManger
from fpl_gaffer.settings import settings
from fpl_gaffer.tools._common import tool_error

logger = logging.getLogger(__name__)


class UserTeamInfoInput(BaseModel):
    manager_id: int = Field(..., description="The user's FPL manager ID.")
    gameweek: int = Field(..., description="The upcoming/current gameweek number from graph context.")


class TransferHistoryInput(BaseModel):
    manager_id: int = Field(..., description="The user's FPL manager ID.")


class CaptainHistoryInput(BaseModel):
    manager_id: int = Field(..., description="The user's FPL manager ID.")
    current_gameweek: int = Field(..., description="The current gameweek number from graph context.")
    num_gameweeks: int = Field(
        settings.MAX_CAPTAIN_HISTORY_GAMEWEEKS,
        description="How many recent gameweeks of captaincy history to return.",
    )


class LeagueStandingsInput(BaseModel):
    league_id: int = Field(..., description="The classic league ID to fetch standings for.")
    page: int = Field(1, description="Standings page number (each page is 50 entries).")


async def get_user_team_info(manager_id: int, gameweek: int) -> Dict | None:
    """Implementation for get_user_team_info_tool. Kept importable for tests."""
    try:
        picks_gameweek = max(1, gameweek - 1)
        team_manager = FPLTeamDataManger(FPLOfficialAPIClient(), manager_id, picks_gameweek)
        return await team_manager.extract_team_data()
    except Exception as e:
        return tool_error(logger, "get_user_team_info", e)


async def get_user_transfer_history(manager_id: int) -> Dict:
    """Implementation for get_user_transfer_history_tool. Kept importable for tests."""
    try:
        team_manager = FPLTeamDataManger(FPLOfficialAPIClient(), manager_id)
        transfers = await team_manager.get_transfer_history()
        return {"manager_id": manager_id, "count": len(transfers), "transfers": transfers}
    except Exception as e:
        return tool_error(logger, "get_user_transfer_history", e)


async def get_user_captain_history(manager_id: int, current_gameweek: int, num_gameweeks: int) -> Dict:
    """Implementation for get_user_captain_history_tool. Kept importable for tests."""
    try:
        team_manager = FPLTeamDataManger(FPLOfficialAPIClient(), manager_id, current_gameweek)
        num_gameweeks = max(1, min(num_gameweeks, settings.MAX_CAPTAIN_HISTORY_GAMEWEEKS))
        picks = await team_manager.get_captain_picks(num_gameweeks=num_gameweeks)
        return {"manager_id": manager_id, "gameweeks_analyzed": num_gameweeks, "picks": picks}
    except Exception as e:
        return tool_error(logger, "get_user_captain_history", e)


async def get_league_standings(league_id: int, page: int) -> Dict:
    """Implementation for get_league_standings_tool. Kept importable for tests."""
    try:
        team_manager = FPLTeamDataManger(FPLOfficialAPIClient(), settings.FPL_MANAGER_ID)
        return await team_manager.get_league_standings(league_id, page)
    except Exception as e:
        return tool_error(logger, "get_league_standings", e)


@tool("get_user_team_info_tool", args_schema=UserTeamInfoInput)
async def get_user_team_info_tool(manager_id: int, gameweek: int) -> Dict | None:
    """Get the user's current squad: starting XI, bench, captain/vice-captain, money in the bank,
    squad value, and this gameweek's transfer cost. Use this whenever you need to know what the
    user actually owns before suggesting transfers, captaincy, or lineup changes. Always pass the
    current gameweek number from context - this tool automatically looks at the last completed
    gameweek's picks internally."""
    return await get_user_team_info(manager_id, gameweek)


@tool("get_user_transfer_history_tool", args_schema=TransferHistoryInput)
async def get_user_transfer_history_tool(manager_id: int) -> Dict:
    """Get the user's transfer history for the season (players in/out, gameweek, cost). Use this
    when the user asks about their own transfer patterns, or you need to avoid re-suggesting a
    player they recently sold."""
    return await get_user_transfer_history(manager_id)


@tool("get_user_captain_history_tool", args_schema=CaptainHistoryInput)
async def get_user_captain_history_tool(manager_id: int, current_gameweek: int, num_gameweeks: int) -> Dict:
    """Get the user's captain/vice-captain picks for their most recent gameweeks. Use this when
    discussing captaincy strategy or reviewing how their captain choices have performed."""
    return await get_user_captain_history(manager_id, current_gameweek, num_gameweeks)


@tool("get_league_standings_tool", args_schema=LeagueStandingsInput)
async def get_league_standings_tool(league_id: int, page: int) -> Dict:
    """Get the standings for one of the user's classic mini-leagues. Use this only when the user
    asks about a specific league or their rank within one - you'll need the league_id, which the
    user must provide or which you should ask for if not already known from context."""
    return await get_league_standings(league_id, page)
