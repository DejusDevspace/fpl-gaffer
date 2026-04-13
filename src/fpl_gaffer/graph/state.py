from typing import Dict, List, Any
from langgraph.graph import MessagesState


class WorkflowState(MessagesState):
    """State for the FPL Gaffer workflow."""

    # User & gameweek context
    user_id: str
    user_data: Dict[str, Any]
    gameweek_data: Dict

    # Tool execution
    tool_calls: List[Dict[str, Any]]
    tool_results: Dict[str, Any]

    # Response generation
    response: str
    summary: str

    # Validation and control flow
    is_retry: bool
    retry_count: int
    validation_passed: bool
    validation_errors: List[str]
    validation_suggestions: List[str]

    # Metrics tracking
    tokens_in: int
    tokens_out: int
    latency_ms: float
    model: str
