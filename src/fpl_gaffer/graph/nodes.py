import json
import logging
from typing import Dict, Literal
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from fpl_gaffer.graph.state import WorkflowState
from fpl_gaffer.modules import (
    FPLOfficialAPIClient, FPLUserProfileManager, FPLDataManager
)
from fpl_gaffer.core.prompts import (
    MESSAGE_ANALYSIS_PROMPT, FPL_GAFFER_SYSTEM_PROMPT,
    RESPONSE_VALIDATION_PROMPT, RESPONSE_RETRY_PROMPT
)
from fpl_gaffer.tools.executor import AsyncToolExecutor
from fpl_gaffer.utils.chains import get_tools_chain, get_gaffer_response_chain, get_response_validation_chain
from fpl_gaffer.utils.helpers import get_chat_model
from fpl_gaffer.settings import settings

logger = logging.getLogger(__name__)


# TODO: Decide nodes
# Nodes would include flow nodes like context injection, memory extraction/injection
# etc...would also consider edges for tool calling or other conditional flows.
async def context_injection_node(state: WorkflowState) -> Dict:
    # Node to get user data, current gw data, etc...initial data for state
    # Use fpl_id from state if available, otherwise fallback to settings for legacy/dev
    fpl_id = state.get("user_id")

    if not fpl_id or state.get("user_data", None) is None:
        # Fallback to settings if no user_id provided (e.g. local dev)
        if not fpl_id:
            fpl_id = settings.FPL_MANAGER_ID

        api = FPLOfficialAPIClient()

        profile_manager = FPLUserProfileManager(api, fpl_id)
        user_data = await profile_manager.extract_user_data()

        # Get gameweek information
        data_manager = FPLDataManager(api)
        gw_data = await data_manager.get_gameweek_data(include_fixtures=False)

        # Update state
        return {
            "user_id": fpl_id,
            "user_data": user_data,
            "gameweek_data": gw_data,
            "is_retry": False
        }

    return {}

async def message_analysis_node(state: WorkflowState) -> Dict:
    # Node to analyze user messages to get tools to be called?
    additional_context = "N/A"
    if state["is_retry"] and not state.get("validation_passed"):
        logger.info("Retrying response due to validation errors")
        # Update to capture errors and suggestions
        additional_context = RESPONSE_RETRY_PROMPT.format(
            validation_errors=state["validation_errors"],
            validation_suggestions=state["validation_suggestions"]
        )
        # Reset retry flag
        state["is_retry"] = False

    # Pass updated prompt to tools chain
    chain = get_tools_chain(MESSAGE_ANALYSIS_PROMPT)

    response = await chain.ainvoke({
        "messages": state["messages"],
        "user_id": state["user_id"],
        "gameweek_number": state["gameweek_data"].get("gameweek", "N/A"),
        "team_name": state["user_data"].get("team_name", "Unknown"),
        "total_points": state["user_data"].get("total_points", "N/A"),
        "overall_rank": state["user_data"].get("overall_rank", "N/A"),
        "additional_context": additional_context
    })

    logger.debug("Message analysis response: %s", response)

    if response.call_tools:
        return {"tool_calls": response.tool_calls}

    return {}

async def tool_execution_node(state: WorkflowState) -> Dict:
    # Node to call tools and return tool results
    # Verify tool calls exist
    if not state.get("tool_calls", None):
        logger.debug("No tool calls to execute")
        return {"tool_results": {}}

    executor = AsyncToolExecutor()
    results = await executor.execute_multiple_tools(state["tool_calls"])

    return {"tool_results": results}


async def summarize_conversation_node(state: WorkflowState) -> Dict:
    # Conditional node to summarize conversation
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

    # Append the summary to the current messages
    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = await model.ainvoke(messages)

    # Remove messages from state
    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-settings.MESSAGES_AFTER_SUMMARY]]
    return {"summary": response.content, "messages": delete_messages}

async def message_generation_node(state: WorkflowState) -> Dict:
    # Node to provide structured response for users
    # Pass updated prompt to gaffer chain
    chain = get_gaffer_response_chain(FPL_GAFFER_SYSTEM_PROMPT)
    response = await chain.ainvoke({
        "messages": state["messages"],
        "user_id": state["user_id"],
        "gameweek_number": state["gameweek_data"].get("gameweek", "N/A"),
        "team_name": state["user_data"].get("team_name", "Unknown"),
        "total_points": state["user_data"].get("total_points", "N/A"),
        "overall_rank": state["user_data"].get("overall_rank", "N/A"),
        "tool_results": json.dumps(state.get("tool_results", "Not applicable"), indent=2)
    })
    logger.debug("Generated response: %s", response)

    return {"response": response.content}

async def response_validation_node(state: WorkflowState) -> Dict:
    # Node to assess response before sending to user (can loop back to tool calls, etc)
    user_info = {
        "user_id": state["user_id"],
        "gameweek_number": state["gameweek_data"].get("gameweek", "N/A"),
        "team_name": state["user_data"].get("team_name", "Unknown"),
        "total_points": state["user_data"].get("total_points", "N/A"),
        "overall_rank": state["user_data"].get("overall_rank", "N/A"),
    }

    if state.get("retry_count", 0) >= settings.MAX_RETRIES:
        logger.info("Max retries reached; skipping validation")
        return {
            "validation_passed": True,
            "validation_errors": [],
            "validation_suggestions": [],
            "messages": AIMessage(content=state["response"])
        }

    chain = get_response_validation_chain(RESPONSE_VALIDATION_PROMPT)

    response = await chain.ainvoke({
        "context": state["messages"],
        "user_info": json.dumps(user_info, indent=2),
        "generated_response": state["response"],
        "tool_results": state.get("tool_results", "")
    })

    logger.debug("Validation response: %s", response)

    if response.validation_passed:
        return {
            "validation_passed": response.validation_passed,
            "validation_errors": response.errors,
            "validation_suggestions": response.suggestions,
            "messages": AIMessage(content=state["response"]),
            "retry_count": 0,
            "tool_calls": [],
            "tool_results": {}
        }
    else:
        return {
            "validation_passed": response.validation_passed,
            "validation_errors": response.errors,
            "validation_suggestions": response.suggestions
        }


def retry_response_node(state: WorkflowState) -> Dict:
    # Node to prepare for response retry
    # Increase retry count, reset tool calls and results, and update retry flag
    return {
        "is_retry": True,
        "retry_count": state.get("retry_count", 0) + 1,
        "tool_results": {},
        "tool_calls": []
    }
