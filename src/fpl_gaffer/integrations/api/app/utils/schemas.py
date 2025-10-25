from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class LinkFPLRequest(BaseModel):
    fpl_id: int
    # team_data: Dict[str, Any]


class SyncFPLRequest(BaseModel):
    fpl_id: int
    # team_data: Dict[str, Any]
    # gameweek_history: List[Dict[str, Any]]
    # transfer_history: List[Dict[str, Any]]
    # captain_picks: List[Dict[str, Any]]


class DashboardResponse(BaseModel):
    team: Dict[str, Any]
    current_gameweek: Optional[Dict[str, Any]]
    gameweek_history: List[Dict[str, Any]]
    transfer_history: List[Dict[str, Any]]
    current_captain: Optional[Dict[str, Any]]

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    request_id: str
