from typing import Literal, Any
from fpl_gaffer.graph.state import WorkflowState
from langgraph.graph import END

def tool_decision(
    state: WorkflowState
) -> Literal["message_generation_node", "tool_execution_node"]:
    # Node to decide whether to go to tool execution node.
    if state.get("tool_calls", {}) is None:
        print("taking message_generation_node")
        return "message_generation_node"
    return "tool_execution_node"

def should_retry_or_end(state: WorkflowState) -> str | Any:
    # Node to decide whether to retry response generation based on validation results
    if state.get("validation_passed", None):
        return END
    return "retry_response_node"
