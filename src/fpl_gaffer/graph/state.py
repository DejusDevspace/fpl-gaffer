from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, List
from datetime import datetime
from langchain.schema import Document
from langgraph.graph import MessagesState
from fpl_gaffer.settings import settings


# TODO: Update state to use MessagesState and refactor variables
class WorkflowState(MessagesState):
    """State for the FPL Gaffer workflow."""

    # Core state variables
    user_id: int
    gameweek: Dict # Gameweek data dict
    tool_calls: List[str]
