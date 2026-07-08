from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class OnboardingRequest(BaseModel):
    name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=5)
    fpl_id: int = Field(..., gt=0)


class OnboardingResponse(BaseModel):
    status: str
    user_id: str
    phone: str
    fpl_id: int
    fpl_team_id: str
    team_name: Optional[str] = None


class LinkFPLRequest(BaseModel):
    fpl_id: int


class SyncFPLRequest(BaseModel):
    fpl_id: int


class DashboardResponse(BaseModel):
    team: Dict[str, Any]
    current_gameweek: Optional[Dict[str, Any]]
    gameweek_history: List[Dict[str, Any]]
    transfer_history: List[Dict[str, Any]]
    current_captain: Optional[Dict[str, Any]]


class LeagueStandingsRequest(BaseModel):
    league_id: int
    page: Optional[int] = 1

class LeaguesResponse(BaseModel):
    classic: List[Dict[str, Any]]
    h2h: Optional[List[Dict[str, Any]]]

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    request_id: str
