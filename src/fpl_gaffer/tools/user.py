from typing import Dict, Optional
from pydantic import BaseModel, Field
from fpl_gaffer.modules import FPLTeamDataManger, FPLOfficialAPIClient
from fpl_gaffer.core.exceptions import ToolError


class UserTeamInfoInput(BaseModel):
    """Input schema for the user team info tool."""
    manager_id: int = Field(..., description="The user's FPL manager ID.")
    gameweek: int = Field(..., description="The upcoming/current gameweek number from graph context.")


async def get_user_team_info_tool(manager_id: int, gameweek: int) -> Dict:
    """Get user team information like budget, squad, transfers, etc."""
    api = FPLOfficialAPIClient()
    picks_gameweek = max(1, gameweek - 1)
    team_manager = FPLTeamDataManger(api, manager_id, picks_gameweek)

    try:
        team_data = await team_manager.extract_team_data()
        return team_data
    except Exception as e:
        raise ToolError(f"Error while using user team info tool: {e}") from e
