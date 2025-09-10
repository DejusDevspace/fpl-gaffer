from typing import Dict, Optional
from pydantic import BaseModel, Field
from fpl_gaffer.modules import FPLTeamDataManger, FPLOfficialAPIClient


class UserTeamInfoInput(BaseModel):
    """Input schema for the user team info tool."""
    manager_id: int = Field(..., description="The user's FPL manager ID.")
    gameweek: int = Field(..., description="The current gameweek number to fetch data for.")


async def get_user_team_info_tool(manager_id: int, gameweek: int) -> Dict:
    """Get user team information like budget, squad, transfers, etc."""
    api = FPLOfficialAPIClient()
    team_manager = FPLTeamDataManger(api, manager_id, gameweek)

    try:
        team_data = await team_manager.extract_team_data()
        return team_data
    except Exception as e:
        raise Exception(f"Error while using user team info tool: {e}") from e
