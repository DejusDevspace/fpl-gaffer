from typing import Literal, Any
from fpl_gaffer.graph.state import WorkflowState
from langgraph.graph import END
from fpl_gaffer.settings import settings

def tool_decision(
    state: WorkflowState
) -> Literal["message_generation_node", "tool_execution_node"]:
    # Node to decide whether to go to tool execution node.
    if state.get("tool_calls", None) is None:
        print("taking message_generation_node")
        return "message_generation_node"
    return "tool_execution_node"

def should_retry_or_summarize(state: WorkflowState) -> str | Any:
    # Node to decide whether to retry response generation based on validation results
    # or to summarize the conversation based on number of messages
    if state.get("validation_passed", None):
        messages = state["messages"]

        if len(messages) > settings.MESSAGES_SUMMARY_TRIGGER:
            return "summarize_conversation_node"

        return END
    return "retry_response_node"

# def should_summarize_conversation(
#     state: WorkflowState
# ) -> Literal["summarize_conversation_node", "__end__"]:
#     # Node to decide whether to summarize the conversation
#     messages = state["messages"]
#
#     if len(messages) > settings.MESSAGES_SUMMARY_TRIGGER:
#         return "summarize_conversation_node"
#
#     return END
