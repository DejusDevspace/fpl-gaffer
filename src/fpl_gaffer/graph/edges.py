from typing import Literal
import logging
from fpl_gaffer.graph.state import WorkflowState
from langgraph.graph import END
from fpl_gaffer.settings import settings

logger = logging.getLogger(__name__)


def should_continue_to_tools(state: WorkflowState) -> Literal["tool_node", "response_validation_node"]:
    """After agent_node: if the model asked for tool calls, execute them and loop back to the
    agent. Otherwise, it produced a final answer - move on to validation."""
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tool_node"
    return "response_validation_node"


def should_retry_or_summarize(state: WorkflowState):
    """After validation: retry (back to agent_node), summarize, or end the turn."""
    if state.get("validation_passed", None):
        messages = state["messages"]
        if len(messages) > settings.MESSAGES_SUMMARY_TRIGGER:
            return "summarize_conversation_node"
        return END
    return "retry_response_node"
