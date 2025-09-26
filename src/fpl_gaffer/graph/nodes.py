import json
from typing import Dict, Literal
from fpl_gaffer.graph.state import WorkflowState
from langchain_core.messages import AIMessage, ToolMessage
from fpl_gaffer.modules import (
    FPLOfficialAPIClient, FPLUserProfileManager, FPLDataManager
)
from fpl_gaffer.core.prompts import MESSAGE_ANALYSIS_PROMPT, FPL_GAFFER_SYSTEM_PROMPT
from fpl_gaffer.tools.executor import AsyncToolExecutor
from fpl_gaffer.utils.chains import get_tools_chain, get_gaffer_response_chain
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
            "gameweek_data": gw_data
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
        "overall_rank": state["user_data"].get("overall_rank", "N/A")
    })

    print("Message analysis response:", response)

    if response.call_tools:
        return {"tool_calls": response.tool_calls}

    return {}

async def tool_execution_node(state: WorkflowState) -> Dict:
    # Node to call tools and return tool results
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

def response_validation_node(state: WorkflowState) -> Dict:
    # Node to assess response before sending to user (can loop back to tool calls, etc)
    pass

# I would select few of the nodes above for use, and merge some eventually.
# Not all would be standalone nodes.
