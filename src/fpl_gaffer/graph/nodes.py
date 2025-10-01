import json
from typing import Dict, Literal
from fpl_gaffer.graph.state import WorkflowState
from langchain_core.messages import AIMessage, ToolMessage
from fpl_gaffer.modules import (
    FPLOfficialAPIClient, FPLUserProfileManager, FPLDataManager
)
from fpl_gaffer.core.prompts import (
    MESSAGE_ANALYSIS_PROMPT, FPL_GAFFER_SYSTEM_PROMPT,
    RESPONSE_VALIDATION_PROMPT, RESPONSE_RETRY_PROMPT
)
from fpl_gaffer.tools.executor import AsyncToolExecutor
from fpl_gaffer.utils.chains import get_tools_chain, get_gaffer_response_chain, get_response_validation_chain
from fpl_gaffer.settings import settings


# TODO: Decide nodes
# Nodes would include flow nodes like context injection, memory extraction/injection
# etc...would also consider edges for tool calling or other conditional flows.
async def context_injection_node(state: WorkflowState) -> Dict:
    # Node to get user data, current gw data, etc...initial data for state
    # Get user id (if not available)
    # Would use ID from config for now, would replace with db implementation much later
    if state.get("user_id", 0) != settings.FPL_MANAGER_ID or state.get("user_data", None) is None:
        # Get user data
        user_id = settings.FPL_MANAGER_ID
        api = FPLOfficialAPIClient()

        profile_manager = FPLUserProfileManager(api, user_id)
        user_data = await profile_manager.extract_user_data()

        # Get gameweek information
        data_manager = FPLDataManager(api)
        gw_data = await data_manager.get_gameweek_data()

        # Update state
        return {
            "user_id": user_id,
            "user_data": user_data,
            "gameweek_data": gw_data,
            "is_retry": False
        }

    return {}

async def message_analysis_node(state: WorkflowState) -> Dict:
    # Node to analyze user messages to get tools to be called?
    # prompt = MESSAGE_ANALYSIS_PROMPT.format(
        # user_id=state["user_id"],
        # gameweek_number=state["gameweek_data"].get("gameweek", "N/A"),
        # team_name=state["user_data"].get("team_name", "Unknown"),
        # total_points=state["user_data"].get("total_points", "N/A"),
        # overall_rank=state["user_data"].get("overall_rank", "N/A")
    # )
    # print("Prompt:\n", prompt)
    # TODO: Handle loop-back from response validation node
    additional_context = "N/A"
    if state["is_retry"] and not state.get("validation_passed"):
        print("Retrying response due to validation errors...")
        # Update to capture errors and suggestions
        additional_context = RESPONSE_RETRY_PROMPT.format(
            validation_errors=state["validation_errors"],
            validation_suggestions=state["validation_suggestions"]
        )
        # Reset retry flag
        state["is_retry"] = False

    # Pass updated prompt to tools chain
    chain = get_tools_chain(MESSAGE_ANALYSIS_PROMPT)

    print(state["messages"][-1:])
    print("State:", state)
    response = await chain.ainvoke({
        "messages": state["messages"],
        "user_id": state["user_id"],
        "gameweek_number": state["gameweek_data"].get("gameweek", "N/A"),
        "team_name": state["user_data"].get("team_name", "Unknown"),
        "total_points": state["user_data"].get("total_points", "N/A"),
        "overall_rank": state["user_data"].get("overall_rank", "N/A"),
        "additional_context": additional_context
    })

    print("Message analysis response:", response)

    if response.call_tools:
        return {"tool_calls": response.tool_calls}

    return {}

async def tool_execution_node(state: WorkflowState) -> Dict:
    # Node to call tools and return tool results
    # Verify tool calls exist
    if not state.get("tool_calls", None):
        print("No tool calls to execute.")
        return {"tool_results": {}}

    executor = AsyncToolExecutor()
    results = await executor.execute_multiple_tools(state["tool_calls"])

    return {"tool_results": results}


async def summarize_conversation_node(state: WorkflowState) -> Dict:
    # Conditional node to summarize conversation
    pass

async def message_generation_node(state: WorkflowState) -> Dict:
    # Node to provide structured response for users
    # prompt = FPL_GAFFER_SYSTEM_PROMPT.format(
    #     user_id=state["user_id"],
    #     gameweek_number=state["gameweek_data"].get("gameweek", "N/A"),
    #     team_name=state["user_data"].get("team_name", "Unknown"),
    #     total_points=state["user_data"].get("total_points", "N/A"),
    #     overall_rank=state["user_data"].get("overall_rank", "N/A"),
    #     tool_results=json.dumps(state.get("tool_results", "Not applicable"), indent=2)
    # )

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
    print("Final Output", response)

    return {"response": response}

async def response_validation_node(state: WorkflowState) -> Dict:
    # Node to assess response before sending to user (can loop back to tool calls, etc)
    chain = get_response_validation_chain(RESPONSE_VALIDATION_PROMPT)
    response = await chain.ainvoke({
        "context": state["messages"],
        "generated_response": state["response"],
        "tool_results": state["tool_results"]
    })

    print("Validation response:", response)

    if response.validation_passed:
        return {
            "validation_passed": response.validation_passed,
            "validation_errors": response.errors,
            "validation_suggestions": response.suggestions,
            "messages": state["response"]
        }
    else:
        return {
            "validation_passed": response.validation_passed,
            "validation_errors": response.errors,
            "validation_suggestions": response.suggestions
        }


def retry_response_node(state: WorkflowState) -> Dict:
    # Node to prepare for response retry
    # Reset tool calls and results and update retry flag
    return {"is_retry": True, "tool_results": {}, "tool_calls": []}

# I would select few of the nodes above for use, and merge some eventually.
# Not all would be standalone nodes.
