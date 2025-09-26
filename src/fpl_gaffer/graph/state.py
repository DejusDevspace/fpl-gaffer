from typing import Optional, Dict, List, Any
from langgraph.graph import MessagesState


class WorkflowState(MessagesState):
    """State for the FPL Gaffer workflow."""

    response: str
    user_id: int
    user_data: Dict[str, Any]
    gameweek_data: Dict
    tool_calls: List[Dict[str, Any]]
    tool_results: Dict[str, Any]

