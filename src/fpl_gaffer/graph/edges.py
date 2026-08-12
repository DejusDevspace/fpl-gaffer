import logging
from typing import Literal
from langgraph.graph import END
from fpl_gaffer.graph.state import WorkflowState
from fpl_gaffer.core.limits import DEFAULT_LIMITS
from fpl_gaffer.utils.tokens import estimate_message_tokens

logger = logging.getLogger(__name__)


def should_continue_to_tools(state: WorkflowState) -> Literal["tool_node", "response_validation_node"]:
    """After agent_node: if the model asked for tool calls, execute them and loop back to the
    agent. Otherwise, it produced a final answer - move on to validation."""
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tool_node"
    return "response_validation_node"


def route_after_validation(state: WorkflowState):
    """After validation: retry, or move on to post-turn cleanup."""
    if state.get("validation_passed", None):
        return "compact_turn_node"
    return "retry_response_node"


def route_after_compact(state: WorkflowState):
    """After cleanup: summarize if the (now-pruned) history is still large, or end the turn."""
    limits = state.get("limits") or DEFAULT_LIMITS
    token_count = estimate_message_tokens(state["messages"])
    if token_count > limits["max_context_tokens_before_summary"]:
        return "summarize_conversation_node"
    return END
