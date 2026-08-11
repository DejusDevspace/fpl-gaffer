from functools import lru_cache
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from fpl_gaffer.graph.state import WorkflowState
from fpl_gaffer.graph.nodes import (
    context_injection_node, agent_node,
    response_validation_node, retry_response_node, summarize_conversation_node,
)
from fpl_gaffer.graph.edges import should_continue_to_tools, should_retry_or_summarize
from fpl_gaffer.tools import TOOLS


@lru_cache(maxsize=1)
def create_workflow_graph():
    """Create the FPL Gaffer workflow graph."""
    graph_builder = StateGraph(WorkflowState)

    tool_node = ToolNode(TOOLS, handle_tool_errors=True)

    graph_builder.add_node("context_injection_node", context_injection_node)
    graph_builder.add_node("agent_node", agent_node)
    graph_builder.add_node("tool_node", tool_node)
    graph_builder.add_node("response_validation_node", response_validation_node)
    graph_builder.add_node("retry_response_node", retry_response_node)
    graph_builder.add_node("summarize_conversation_node", summarize_conversation_node)

    graph_builder.set_entry_point("context_injection_node")

    graph_builder.add_edge("context_injection_node", "agent_node")
    graph_builder.add_conditional_edges("agent_node", should_continue_to_tools)
    graph_builder.add_edge("tool_node", "agent_node")
    graph_builder.add_conditional_edges("response_validation_node", should_retry_or_summarize)
    graph_builder.add_edge("retry_response_node", "agent_node")
    graph_builder.add_edge("summarize_conversation_node", END)

    return graph_builder


# Compile the graph for LangGraph studio
graph = create_workflow_graph().compile()
