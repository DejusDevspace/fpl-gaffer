import json
import logging
from typing import Dict
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from fpl_gaffer.graph.state import WorkflowState
from fpl_gaffer.modules import (
    FPLOfficialAPIClient, FPLUserProfileManager, FPLDataManager
)
from fpl_gaffer.core.prompts import (
    FPL_GAFFER_SYSTEM_PROMPT, RESPONSE_VALIDATION_PROMPT, RESPONSE_RETRY_PROMPT
)
from fpl_gaffer.utils.chains import get_agent_chain, get_response_validation_chain
from fpl_gaffer.utils.helpers import get_chat_model
from fpl_gaffer.settings import settings

logger = logging.getLogger(__name__)


async def context_injection_node(state: WorkflowState) -> Dict:
    """Get user data, current gameweek data, etc. Unchanged from before."""
    fpl_id = int(state.get("user_id"))

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

        return {
            "user_id": fpl_id,
            "user_data": user_data,
            "gameweek_data": gw_data,
            "is_retry": False,
        }

    return {}


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
    run more than once per user turn — each pass through tool_node loops back here."""
    retry_feedback = ""
    if state.get("is_retry") and not state.get("validation_passed", True):
        logger.info("Retrying response due to validation errors")
        retry_feedback = RESPONSE_RETRY_PROMPT.format(
            validation_errors=state.get("validation_errors", []),
            validation_suggestions=state.get("validation_suggestions", []),
        )

    chain = get_agent_chain(FPL_GAFFER_SYSTEM_PROMPT)

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

    return {
        "messages": [response],
        "is_retry": False,
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


async def response_validation_node(state: WorkflowState) -> Dict:
    """Validate the model's final answer (the last message in state, which agent_node just
    produced with no further tool calls) against the tool results already present earlier in the
    message history."""
    user_info = {
        "user_id": state["user_id"],
        "gameweek_number": state["gameweek_data"].get("gameweek", "N/A"),
        "team_name": state["user_data"].get("team_name", "Unknown"),
        "total_points": state["user_data"].get("total_points", "N/A"),
        "overall_rank": state["user_data"].get("overall_rank", "N/A"),
    }

    final_message = state["messages"][-1]

    if state.get("retry_count", 0) >= settings.MAX_RETRIES:
        logger.info("Max retries reached; skipping validation")
        return {
            "validation_passed": True,
            "validation_errors": [],
            "validation_suggestions": [],
            "response": final_message.content,
            "retry_count": 0,
        }

    chain = get_response_validation_chain(RESPONSE_VALIDATION_PROMPT)

    response = await chain.ainvoke({
        "context": state["messages"][:-1],
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


def retry_response_node(state: WorkflowState) -> Dict:
    """Flag the next agent_node pass as a retry; the feedback itself is injected into the system
    prompt inside agent_node (see retry_feedback), not appended as a fake conversation turn."""
    return {
        "is_retry": True,
        "retry_count": state.get("retry_count", 0) + 1,
    }
