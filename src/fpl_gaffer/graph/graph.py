from functools import lru_cache
from fpl_gaffer.settings import settings
from langgraph.graph import StateGraph, START, END
from fpl_gaffer.graph.state import WorkflowState
from fpl_gaffer.graph.nodes import (
    context_injection_node, message_analysis_node, tool_execution_node,
    message_generation_node, response_validation_node, retry_response_node
)
from fpl_gaffer.graph.edges import tool_decision, should_retry_or_end

@lru_cache(maxsize=1)
def create_workflow_graph():
    """Create the data collector workflow graph."""
    graph_builder = StateGraph(WorkflowState)

    # Add nodes
    graph_builder.add_node("context_injection_node", context_injection_node)
    graph_builder.add_node("message_analysis_node", message_analysis_node)
    graph_builder.add_node("tool_execution_node", tool_execution_node)
    graph_builder.add_node("message_generation_node", message_generation_node)
    graph_builder.add_node("response_validation_node", response_validation_node)
    graph_builder.add_node("retry_response_node", retry_response_node)

    # Define the workflow
    # Set the graph entry point
    graph_builder.set_entry_point("context_injection_node")

    graph_builder.add_edge("context_injection_node", "message_analysis_node")

    graph_builder.add_conditional_edges("message_analysis_node", tool_decision)

    graph_builder.add_edge("tool_execution_node", "message_generation_node")
    graph_builder.add_edge("message_generation_node", "response_validation_node")
    graph_builder.add_conditional_edges("response_validation_node", should_retry_or_end)
    graph_builder.add_edge("retry_response_node", "message_analysis_node")

    return graph_builder
