from functools import lru_cache

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from fpl_gaffer.graph.edges import route_after_compact, route_after_validation, should_continue_to_tools
from fpl_gaffer.graph.nodes import (
    agent_node,
    compact_turn_node,
    context_injection_node,
    response_validation_node,
    retry_response_node,
    summarize_conversation_node,
)
from fpl_gaffer.graph.state import WorkflowState
from fpl_gaffer.settings import settings
from fpl_gaffer.tools import TOOLS


@lru_cache(maxsize=1)
def create_workflow_graph():
    """Create the FPL Gaffer workflow graph builder (uncompiled)."""
    graph_builder = StateGraph(WorkflowState)

    tool_node = ToolNode(TOOLS, handle_tool_errors=True)

    graph_builder.add_node("context_injection_node", context_injection_node)
    graph_builder.add_node("agent_node", agent_node)
    graph_builder.add_node("tool_node", tool_node)
    graph_builder.add_node("response_validation_node", response_validation_node)
    graph_builder.add_node("retry_response_node", retry_response_node)
    graph_builder.add_node("summarize_conversation_node", summarize_conversation_node)
    graph_builder.add_node("compact_turn_node", compact_turn_node)

    graph_builder.set_entry_point("context_injection_node")

    graph_builder.add_edge("context_injection_node", "agent_node")
    graph_builder.add_conditional_edges("agent_node", should_continue_to_tools)
    graph_builder.add_edge("tool_node", "agent_node")
    graph_builder.add_conditional_edges("response_validation_node", route_after_validation)
    graph_builder.add_conditional_edges("compact_turn_node", route_after_compact)
    graph_builder.add_edge("retry_response_node", "agent_node")
    graph_builder.add_edge("summarize_conversation_node", END)

    return graph_builder


_checkpointer_cm = None
_compiled_graph = None


async def get_compiled_graph():
    """Get (or lazily create) the compiled graph with a live Postgres checkpointer.
    Call once at app startup and reuse — don't call this per-request."""
    global _checkpointer_cm, _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph

    _checkpointer_cm = AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)
    checkpointer = await _checkpointer_cm.__aenter__()
    await checkpointer.setup()  # creates checkpoint tables if they don't exist yet - idempotent

    _compiled_graph = create_workflow_graph().compile(checkpointer=checkpointer)
    return _compiled_graph


async def close_graph():
    """Call on app shutdown to close the checkpointer's connection pool cleanly."""
    global _checkpointer_cm
    if _checkpointer_cm is not None:
        await _checkpointer_cm.__aexit__(None, None, None)


async def make_graph(config: dict | None = None):
    """LangGraph CLI / Studio entry point. `langgraph dev` supports pointing at an async factory
    like this instead of a bare compiled graph, specifically for graphs that need async setup
    (here: opening the Postgres checkpointer pool) before they're usable. `config` is accepted to
    match the CLI's expected call signature but isn't used - we don't vary graph construction per
    request. This just delegates to the same get_compiled_graph() the production app uses, so
    Studio and Railway are exercising the exact same checkpointer-backed graph, not two different
    code paths."""
    return await get_compiled_graph()
