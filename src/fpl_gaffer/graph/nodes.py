import json
import logging
from typing import Dict
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, ToolMessage
from fpl_gaffer.graph.state import WorkflowState
from fpl_gaffer.modules import (
    FPLOfficialAPIClient, FPLUserProfileManager, FPLDataManager
)
from fpl_gaffer.core.prompts import (
    FPL_GAFFER_SYSTEM_PROMPT, RESPONSE_VALIDATION_PROMPT, RESPONSE_RETRY_PROMPT
)
from fpl_gaffer.core.limits import resolve_limits, DEFAULT_LIMITS
from fpl_gaffer.utils.chains import get_agent_chain, get_response_validation_chain
from fpl_gaffer.utils.helpers import get_chat_model
from fpl_gaffer.settings import settings

logger = logging.getLogger(__name__)

BUDGET_EXCEEDED_NOTE = (
    "\n\n[Internal note - not part of the user's message. You've used all the tool calls "
    "available for this turn. Answer now using only the information already gathered above - "
    "do not attempt further tool calls.]"
)


async def context_injection_node(state: WorkflowState) -> Dict:
    """Get user data, current gameweek data, etc., and reset per-turn cost-control state."""
    fpl_id = int(state.get("user_id"))

    result: Dict = {
        "limits": await resolve_limits(str(fpl_id)),
        "tool_calls_this_turn": 0,
    }

    if not fpl_id or state.get("user_data", None) is None:
        if not fpl_id:
            if settings.DEBUG:
                logger.warning("No user_id in graph state; falling back to settings.FPL_MANAGER_ID (DEBUG mode)")
                fpl_id = int(settings.FPL_MANAGER_ID)
            else:
                raise ValueError("No FPL user ID provided and DEBUG mode is off — cannot fall back to default.")

        api = FPLOfficialAPIClient()
        profile_manager = FPLUserProfileManager(api, fpl_id)
        user_data = await profile_manager.extract_user_data()

        data_manager = FPLDataManager(api)
        gw_data = await data_manager.get_gameweek_data(include_fixtures=False)

        result.update({
            "user_id": fpl_id,
            "user_data": user_data,
            "gameweek_data": gw_data,
            "is_retry": False,
        })

    return result


def _extract_token_usage(message: AIMessage) -> Dict:
    """Best-effort extraction of real token usage from a ChatGroq response."""
    usage = getattr(message, "usage_metadata", None) or {}
    if usage:
        return {
            "tokens_in": usage.get("input_tokens", 0),
            "tokens_out": usage.get("output_tokens", 0),
        }

    token_usage = (message.response_metadata or {}).get("token_usage", {})
    return {
        "tokens_in": token_usage.get("prompt_tokens", 0),
        "tokens_out": token_usage.get("completion_tokens", 0),
    }


async def agent_node(state: WorkflowState) -> Dict:
    """Single agent turn: the model sees the full conversation (including any tool results from
    a previous loop iteration) and either calls tool(s) or produces a final answer. This node may
    run more than once per user turn — each pass through tool_node loops back here.

    When the tool-call budget is exhausted, tools are unbound from the model so it's forced to
    produce a content-only answer using what it already has."""
    limits = state.get("limits") or DEFAULT_LIMITS
    budget_exceeded = state.get("tool_calls_this_turn", 0) >= limits["max_tool_calls_per_turn"]

    retry_feedback = ""
    if state.get("is_retry") and not state.get("validation_passed", True):
        logger.info("Retrying response due to validation errors")
        retry_feedback = RESPONSE_RETRY_PROMPT.format(
            validation_errors=state.get("validation_errors", []),
            validation_suggestions=state.get("validation_suggestions", []),
        )

    if budget_exceeded:
        retry_feedback += BUDGET_EXCEEDED_NOTE

    chain = get_agent_chain(
        FPL_GAFFER_SYSTEM_PROMPT,
        bind_tools=not budget_exceeded
    )

    response = await chain.ainvoke({
        "messages": state["messages"],
        "user_id": state["user_id"],
        "gameweek_number": state["gameweek_data"].get("gameweek", "N/A"),
        "team_name": state["user_data"].get("team_name", "Unknown"),
        "total_points": state["user_data"].get("total_points", "N/A"),
        "overall_rank": state["user_data"].get("overall_rank", "N/A"),
        "retry_feedback": retry_feedback,
    })

    usage = _extract_token_usage(response)
    model_name = (response.response_metadata or {}).get("model_name", settings.GROQ_MODEL_NAME)
    new_tool_calls = len(getattr(response, "tool_calls", None) or [])

    return {
        "messages": [response],
        "is_retry": False,
        "tool_calls_this_turn": state.get("tool_calls_this_turn", 0) + new_tool_calls,
        "tokens_in": state.get("tokens_in", 0) + usage["tokens_in"],
        "tokens_out": state.get("tokens_out", 0) + usage["tokens_out"],
        "model": model_name,
    }


async def summarize_conversation_node(state: WorkflowState) -> Dict:
    """Conditional node to summarize conversation. Unchanged in behavior; only runs once a turn
    is fully resolved (validation passed, no dangling tool calls), so trimming messages here is
    always safe."""
    model = get_chat_model()
    summary = state.get("summary", "")

    if summary:
        summary_message = (
            f"This is the summary of the conversation to date between Gaffer and the user:{summary}\n\n"
            "Extend the summary by taking into account the new messages above:"
        )
    else:
        summary_message = (
            "Create a summary of the conversation above between Gaffer and the user. "
            "The summary must be a short description of the conversation so far, "
            "but that captures all the relevant information shared between Gaffer and the user:"
        )

    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = await model.ainvoke(messages)

    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-settings.MESSAGES_AFTER_SUMMARY]]
    return {"summary": response.content, "messages": delete_messages}


def _last_human_message_index(messages) -> int:
    """Find the index of the last HumanMessage in the list."""
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            return i
    return 0


async def response_validation_node(state: WorkflowState) -> Dict:
    """Validate the model's final answer against the tool results from this turn only.

    Skips the LLM call entirely when no tools were used this turn (nothing to hallucinate from),
    and scopes the validation context to this turn's exchange rather than the full conversation."""
    final_message = state["messages"][-1]

    # Nothing was fetched via a tool this turn, so there's nothing to hallucinate from a data
    # standpoint - skip the validation LLM call and its full-history payload entirely.
    if state.get("tool_calls_this_turn", 0) == 0:
        return {
            "validation_passed": True,
            "validation_errors": [],
            "validation_suggestions": [],
            "response": final_message.content,
            "retry_count": 0,
        }

    if state.get("retry_count", 0) >= settings.MAX_RETRIES:
        logger.info("Max retries reached; skipping validation")
        return {
            "validation_passed": True,
            "validation_errors": [],
            "validation_suggestions": [],
            "response": final_message.content,
            "retry_count": 0,
        }

    user_info = {
        "user_id": state["user_id"],
        "gameweek_number": state["gameweek_data"].get("gameweek", "N/A"),
        "team_name": state["user_data"].get("team_name", "Unknown"),
        "total_points": state["user_data"].get("total_points", "N/A"),
        "overall_rank": state["user_data"].get("overall_rank", "N/A"),
    }

    # Only this turn's exchange, not the whole conversation - the validator only needs to check
    # this turn's tool grounding, not re-read every prior turn's already-validated history.
    turn_start = _last_human_message_index(state["messages"])
    turn_context = state["messages"][turn_start:-1]

    chain = get_response_validation_chain(RESPONSE_VALIDATION_PROMPT)
    response = await chain.ainvoke({
        "context": turn_context,
        "user_info": json.dumps(user_info, indent=2),
        "generated_response": final_message.content,
    })

    logger.debug("Validation response: %s", response)

    if response.validation_passed:
        return {
            "validation_passed": True,
            "validation_errors": [],
            "validation_suggestions": [],
            "response": final_message.content,
            "retry_count": 0,
        }

    return {
        "validation_passed": False,
        "validation_errors": response.errors,
        "validation_suggestions": response.suggestions,
    }


async def compact_turn_node(state: WorkflowState) -> Dict:
    """Once a turn is fully resolved (validated or max-retries-exhausted), strip this turn's
    intermediate tool-call messages out of long-term history. Keeps the final human question and
    final answer; drops the ToolMessages and any AIMessage tool-call steps in between. This is
    what stops tool payloads from compounding across a conversation - without it, every past
    tool result gets resent on every future turn until the message-count summarizer eventually
    catches up."""
    turn_start = _last_human_message_index(state["messages"])
    turn_messages = state["messages"][turn_start + 1:]

    to_remove = [
        RemoveMessage(id=m.id)
        for m in turn_messages
        if isinstance(m, ToolMessage) or (isinstance(m, AIMessage) and getattr(m, "tool_calls", None))
    ]

    return {"messages": to_remove} if to_remove else {}


def retry_response_node(state: WorkflowState) -> Dict:
    """Flag the next agent_node pass as a retry; the feedback itself is injected into the system
    prompt inside agent_node (see retry_feedback), not appended as a fake conversation turn."""
    return {
        "is_retry": True,
        "retry_count": state.get("retry_count", 0) + 1,
    }
