from typing import Literal, List, Dict
from pydantic import BaseModel, Field
from fpl_gaffer.modules import FPLDataManager, FPLOfficialAPIClient
from fpl_gaffer.core.exceptions import ToolError

class PlayerByPositionInput(BaseModel):
    """Input schema for the player by position tool."""
    position: Literal["GKP", "DEF", "MID", "FWD"] = Field(..., description="Position to search for. One of: GK, DEF, MID, FWD.")
    max_price: float = Field(15.0, description="Maximum player price to search for in millions.")


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

# TODO: Get player data toold
# TODO: Get fixtures data tool (next x gameweeks, difficulty ratings)
