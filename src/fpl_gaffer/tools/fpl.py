from typing import Literal, List, Dict
from pydantic import BaseModel, Field
from fpl_gaffer.modules import FPLDataManager, FPLOfficialAPIClient
from fpl_gaffer.core.exceptions import ToolError

class PlayerByPositionInput(BaseModel):
    """Input schema for the player by position tool."""
    position: Literal["GKP", "DEF", "MID", "FWD"] = Field(..., description="Position to search for. One of: GK, DEF, MID, FWD.")
    max_price: float = Field(15.0, description="Maximum player price to search for in millions.")


class PlayerDataInput(BaseModel):
    """Input schema for the player data tool."""
    player_names: List[str] = Field(..., description="List of player(s) names to fetch data for.")


class FixturesForRangeInput(BaseModel):
    """Input schema for the fixtures for range tool."""
    num_gameweeks: int = Field(..., description="Number of upcoming gameweeks to fetch fixtures for.")


async def get_players_by_position_tool(
    position: Literal["GKP", "DEF", "MID", "FWD"],
    max_price: float
) -> List[Dict]:
    """Get players by position and max price."""
    api = FPLOfficialAPIClient()
    data_manager = FPLDataManager(api)

    try:
        players = await data_manager.get_players_by_position(position, max_price)
        return players
    except Exception as e:
        raise ToolError(f"Error while using player by position tool: {e}") from e

async def get_player_data_tool(player_names: List[str]) -> List[Dict]:
    """Get detailed player data including stats, form, and injuries."""
    api = FPLOfficialAPIClient()
    data_manager = FPLDataManager(api)

    try:
        player_data = await data_manager.get_player_data(player_names)
        return player_data
    except Exception as e:
        raise ToolError(f"Error while using player data tool: {e}") from e

async def get_fixtures_for_range_tool(num_gameweeks: int) -> Dict:
    """Get fixtures from the current gameweek to the next x gameweeks."""
    api = FPLOfficialAPIClient()
    data_manager = FPLDataManager(api)

    try:
        fixtures = await data_manager.get_fixtures_for_range(num_gameweeks)
        return fixtures
    except Exception as e:
        raise ToolError(f"Error while using fixtures for range tool: {e}") from e
