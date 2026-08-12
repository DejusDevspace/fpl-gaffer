from typing import Literal, List, Dict
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from fpl_gaffer.modules import FPLDataManager, FPLOfficialAPIClient
from fpl_gaffer.settings import settings


class PlayerByPositionInput(BaseModel):
    position: Literal["GKP", "DEF", "MID", "FWD"] = Field(
        ..., description="Position to search for."
    )
    max_price: float = Field(16.0, description="Maximum player price to search for, in millions.")


class PlayerDataInput(BaseModel):
    player_names: List[str] = Field(..., description="List of player name(s) to fetch data for.")


class FixturesForRangeInput(BaseModel):
    num_gameweeks: int = Field(..., description="Number of upcoming gameweeks to fetch fixtures for.")


class PlayerFormInput(BaseModel):
    player_names: List[str] = Field(..., description="Player name(s) to get recent form for.")
    num_gameweeks: int = Field(
        settings.MAX_FORM_GAMEWEEKS // 2,
        description="How many of the player's most recent completed gameweeks to analyze.",
    )


class ComparePlayersInput(BaseModel):
    player_names: List[str] = Field(
        ..., description="2-5 player names to compare head to head."
    )
    num_gameweeks_form: int = Field(
        5, description="How many recent gameweeks to use for the form-average part of the comparison."
    )


class PriceMoversInput(BaseModel):
    direction: Literal["rising", "falling"] = Field(
        "rising", description="Whether to find players whose price is rising or falling."
    )
    limit: int = Field(8, description="Max number of players to return.")


class DifferentialCandidatesInput(BaseModel):
    position: Literal["GKP", "DEF", "MID", "FWD"] = Field(..., description="Position to search for.")
    max_price: float = Field(16.0, description="Maximum player price, in millions.")
    max_ownership_percent: float = Field(
        10.0, description="Only include players owned by at most this percent of managers."
    )
    min_form: float = Field(3.0, description="Only include players with at least this form score.")


async def get_players_by_position(
    position:  Literal["GKP", "DEF", "MID", "FWD"],
    max_price: float
) -> Dict:
    """Implementation for get_players_by_position_tool. Kept importable for tests."""
    try:
        data_manager = FPLDataManager(FPLOfficialAPIClient())
        return await data_manager.get_players_by_position(position, max_price)
    except Exception as e:
        return {"error": f"Error while fetching players by position: {e}"}


async def get_player_data(player_names: List[str]) -> List[Dict] | Dict:
    """Implementation for get_player_data_tool. Kept importable for tests."""
    try:
        data_manager = FPLDataManager(FPLOfficialAPIClient())
        return await data_manager.get_player_data(player_names)
    except Exception as e:
        return {"error": f"Error while fetching player data: {e}"}


async def get_fixtures_for_range(num_gameweeks: int) -> Dict:
    """Implementation for get_fixtures_for_range_tool. Kept importable for tests."""
    try:
        data_manager = FPLDataManager(FPLOfficialAPIClient())
        return await data_manager.get_fixtures_for_range(num_gameweeks)
    except Exception as e:
        return {"error": f"Error while fetching fixtures: {e}"}


async def get_player_form(player_names: List[str], num_gameweeks: int) -> Dict:
    """Implementation for get_player_form_tool. Kept importable for tests."""
    try:
        data_manager = FPLDataManager(FPLOfficialAPIClient())
        return await data_manager.get_player_gameweek_history(player_names, num_gameweeks)
    except Exception as e:
        return {"error": f"Error while fetching player form: {e}"}


async def compare_players(player_names: List[str], num_gameweeks_form: int) -> Dict:
    """Implementation for compare_players_tool. Kept importable for tests."""
    try:
        data_manager = FPLDataManager(FPLOfficialAPIClient())
        return await data_manager.compare_players(player_names, num_gameweeks_form)
    except Exception as e:
        return {"error": f"Error while comparing players: {e}"}


async def get_price_movers(direction: Literal["rising", "falling"], limit: int) -> Dict:
    """Implementation for get_price_movers_tool. Kept importable for tests."""
    try:
        data_manager = FPLDataManager(FPLOfficialAPIClient())
        return await data_manager.get_price_movers(direction, limit)
    except Exception as e:
        return {"error": f"Error while fetching price movers: {e}"}


async def get_differential_candidates(
    position:  Literal["GKP", "DEF", "MID", "FWD"],
    max_price: float,
    max_ownership_percent: float,
    min_form: float
) -> Dict:
    """Implementation for get_differential_candidates_tool. Kept importable for tests."""
    try:
        data_manager = FPLDataManager(FPLOfficialAPIClient())
        return await data_manager.get_differential_candidates(
            position, max_price, max_ownership_percent, min_form
        )
    except Exception as e:
        return {"error": f"Error while fetching differential candidates: {e}"}


@tool("get_players_by_position_tool", args_schema=PlayerByPositionInput)
async def get_players_by_position_tool(
    position:  Literal["GKP", "DEF", "MID", "FWD"], max_price: float
) -> Dict:
    """Get players by position and max price, sorted by points/form/ownership. Use this for
    transfer replacement ideas when you know the position and budget but not specific names."""
    return await get_players_by_position(position, max_price)


@tool("get_player_data_tool", args_schema=PlayerDataInput)
async def get_player_data_tool(player_names: List[str]) -> List[Dict] | Dict:
    """Get season-to-date stats, price, and status/injury news for specific named players. Use
    this when the user names players directly."""
    return await get_player_data(player_names)


@tool("get_fixtures_for_range_tool", args_schema=FixturesForRangeInput)
async def get_fixtures_for_range_tool(num_gameweeks: int) -> Dict:
    """Get upcoming fixtures (with difficulty ratings) from the current gameweek forward. Use this
    for fixture-swing or run-of-games planning."""
    return await get_fixtures_for_range(num_gameweeks)


@tool("get_player_form_tool", args_schema=PlayerFormInput)
async def get_player_form_tool(player_names: List[str], num_gameweeks: int) -> Dict:
    """Get named player(s)' gameweek-by-gameweek trend (points, minutes, goals, assists, bonus)
    over their last N completed gameweeks. Use this whenever recent form matters more than the
    season total - e.g. judging a hot streak, a dip in minutes, or a player returning from injury."""
    return await get_player_form(player_names, num_gameweeks)


@tool("compare_players_tool", args_schema=ComparePlayersInput)
async def compare_players_tool(player_names: List[str], num_gameweeks_form: int) -> Dict:
    """Compare 2-5 named players side by side on season stats and recent-form averages. Use this
    whenever the user is choosing between specific named players (e.g. "X or Y for my captain",
    "should I keep A or bring in B")."""
    return await compare_players(player_names, num_gameweeks_form)


@tool("get_price_movers_tool", args_schema=PriceMoversInput)
async def get_price_movers_tool(direction: Literal["rising", "falling"], limit: int) -> Dict:
    """Get players whose price is currently rising or falling the most this gameweek. Use this
    when timing of a transfer matters (buy before a rise, sell before a fall) or the user asks
    about price changes directly."""
    return await get_price_movers(direction, limit)


@tool("get_differential_candidates_tool", args_schema=DifferentialCandidatesInput)
async def get_differential_candidates_tool(
    position:  Literal["GKP", "DEF", "MID", "FWD"],
    max_price: float,
    max_ownership_percent: float,
    min_form: float
) -> Dict:
    """Find low-ownership players with strong current numbers for a position and budget - pure
    stats-based differential candidates, not sourced from expert/scout content. Use this when
    exploring differentials or when the user explicitly asks for something off the beaten path.
    These are numbers-based ideas, not mainstream picks - present them as an optional, flagged
    suggestion the user can choose to act on, not as the primary recommendation."""
    return await get_differential_candidates(position, max_price, max_ownership_percent, min_form)
