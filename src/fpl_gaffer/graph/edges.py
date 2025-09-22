from typing import Literal
from fpl_gaffer.graph.graph import WorkflowState

async def tool_decision(
    state: WorkflowState
) -> Literal["message_generation_node", "tool_execution_node"]:
    # Node to decide whether to go to tool execution node.
    if state["tool_calls"] is None:
        print("taking message_generation_node")
        return "message_generation_node"
    return "tool_execution_node"
