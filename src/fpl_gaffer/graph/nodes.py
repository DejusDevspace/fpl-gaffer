import json
from typing import Dict, Literal
from fpl_gaffer.graph.state import WorkflowState
from langchain_core.messages import AIMessage, ToolMessage
from fpl_gaffer.modules import (
    FPLOfficialAPIClient, FPLUserProfileManager, FPLDataManager
)
from fpl_gaffer.tools.executor import AsyncToolExecutor
from fpl_gaffer.utils.chains import get_tools_chain, get_gaffer_response_chain
from fpl_gaffer.settings import settings
from fpl_gaffer.utils.helpers import get_chat_model


# TODO: Decide nodes
# Nodes would include flow nodes like context injection, memory extraction/injection
# etc...would also consider edges for tool calling or other conditional flows.
async def context_injection_node(state: WorkflowState) -> Dict:
    # Node to get user data, current gw data, etc...initial data for state
    if state.get("user_id", None) is None or state.get("gameweek", None) is None:
        # Use manager ID from setting for now
        user_id = settings.FPL_MANAGER_ID
        api = FPLOfficialAPIClient()
        data_manager = FPLDataManager(api)
        gameweek_data = await data_manager.get_gameweek_data()

        return {"user_id": user_id, "gameweek": gameweek_data}

    return {}

async def message_analysis_node(state: WorkflowState) -> Dict:
    # Node to analyze user messages to get tools to be called?
    chain = get_tools_chain()
    print(state["messages"][-1:])
    response = await chain.ainvoke({"messages": state["messages"][-1:]})

    print("LLM response:", response)

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
    model = get_chat_model()
    response_prompt = f"""
            You are FPL Gaffer, a Fantasy Premier League assistant. Provide a helpful, context-aware response.

            User Message: "{state["messages"]}"

            User's FPL Context:
            {state["user_id"], state["gameweek"]}

            Tool Results:
            {state["tool_results"]}

            Guidelines:
            1. Be conversational and friendly
            2. Provide specific, actionable advice based on the user's actual team
            3. Reference specific players, fixtures, or data when relevant
            4. If suggesting transfers, consider the user's budget and team needs
            5. For captain recommendations, explain your reasoning
            6. Keep responses concise but informative
            7. If there are errors in tool results, gracefully handle them

            Generate a WhatsApp-friendly response (no markdown, casual tone).
            """

    response = await model.apredict(response_prompt)
    state["tool_results"] = {}
    state["tool_calls"] = []
    return {"response": response}

def response_validation_node(state: WorkflowState) -> Dict:
    # Node to assess response before sending to user (can loop back to tool calls, etc)
    pass

# I would select few of the nodes above for use, and merge some eventually.
# Not all would be standalone nodes.
