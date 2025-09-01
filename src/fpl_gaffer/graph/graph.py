from functools import lru_cache
from fpl_gaffer.settings import settings
from langgraph.graph import StateGraph, START, END
from fpl_gaffer.graph.state import WorkflowState
from fpl_gaffer.graph.nodes import (
    fetch_fpl_data_node,
    fetch_user_data_node,
    search_news_node
)

@lru_cache(maxsize=1)
def create_workflow_graph():
    """Create the data collector workflow graph."""
    graph_builder = StateGraph(WorkflowState)

    # Add nodes
    graph_builder.add_node("fetch_fpl_data_node", fetch_fpl_data_node)
    graph_builder.add_node("fetch_user_data_node", fetch_user_data_node)
    graph_builder.add_node("search_news_node", search_news_node)

    # Create the workflow
    graph_builder.add_edge(START, "fetch_fpl_data_node")
    graph_builder.add_edge("fetch_fpl_data_node", "fetch_user_data_node")
    # graph_builder.add_edge("fetch_user_data_node", "search_news_node")
    # graph_builder.add_edge("search_news_node", END)
    graph_builder.add_edge("fetch_user_data_node", END)
    return graph_builder
