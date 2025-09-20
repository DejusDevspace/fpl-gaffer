from functools import lru_cache
from fpl_gaffer.settings import settings
from langgraph.graph import StateGraph, START, END
from fpl_gaffer.graph.state import WorkflowState
from fpl_gaffer.graph.nodes import (
    fetch_fpl_data_node,
    fetch_user_data_node,
    search_news_node,
    process_news_node
)

@lru_cache(maxsize=1)
def create_workflow_graph():
    """Create the data collector workflow graph."""
    graph_builder = StateGraph(WorkflowState)

    # Add nodes

    # Create the workflow

    return graph_builder
