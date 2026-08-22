import logging
from functools import lru_cache

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

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

logger = logging.getLogger(__name__)


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


_checkpointer_pool = None
_compiled_graph = None


async def get_compiled_graph():
    """Get (or lazily create) the compiled graph with a Postgres checkpointer if available,
    falling back gracefully to MemorySaver if DATABASE_URL is unavailable or fails to connect."""
    global _checkpointer_pool, _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph

    if settings.DATABASE_URL:
        try:
            pool = AsyncConnectionPool(
                conninfo=settings.DATABASE_URL,
                max_size=10,
                kwargs={"autocommit": True, "prepare_threshold": None, "row_factory": dict_row},
                open=False,
            )
            await pool.open()
            _checkpointer_pool = pool
            checkpointer = AsyncPostgresSaver(conn=pool)
            await checkpointer.setup()  # creates checkpoint tables if they don't exist yet - idempotent

            _compiled_graph = create_workflow_graph().compile(checkpointer=checkpointer)
            logger.info("Successfully initialized Postgres checkpointer.")
            return _compiled_graph
        except Exception as e:
            logger.error(
                f"Failed to initialize Postgres checkpointer with DATABASE_URL: {e}. "
                "Falling back to MemorySaver."
            )
            if _checkpointer_pool is not None:
                try:
                    await _checkpointer_pool.close()
                except Exception:
                    pass
                _checkpointer_pool = None

    logger.warning("No Postgres checkpointer configured or connection failed. Using MemorySaver fallback.")
    memory_checkpointer = MemorySaver()
    _compiled_graph = create_workflow_graph().compile(checkpointer=memory_checkpointer)
    return _compiled_graph


async def close_graph():
    """Call on app shutdown to close the checkpointer's connection pool cleanly."""
    global _checkpointer_pool
    if _checkpointer_pool is not None:
        try:
            await _checkpointer_pool.close()
        except Exception as e:
            logger.warning(f"Error closing checkpointer connection: {e}")
        _checkpointer_pool = None


async def make_graph(config: dict | None = None):
    """LangGraph CLI / Studio entry point."""
    return await get_compiled_graph()
