from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from fpl_gaffer.utils.helpers import get_chat_model
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from fpl_gaffer.core.prompts import FPL_GAFFER_SYSTEM_PROMPT, MESSAGE_ANALYSIS_PROMPT
from fpl_gaffer.settings import settings

class ToolAnalysis(BaseModel):
    """Result of analysing a user-message for potential tool calls."""
    call_tools: bool = Field(
        ...,
        description="Whether tool(s) needs to be called."
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        ...,
        description="The formatted tool(s) to call."
    )


def get_tools_chain():
    """Create a chain to analyze user message and return structured tool analysis output."""
    model = get_chat_model().with_structured_output(ToolAnalysis)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", MESSAGE_ANALYSIS_PROMPT),
            MessagesPlaceholder(variable_name="messages")
        ]
    )

    return prompt | model

def get_gaffer_response_chain():
    """Create a response generation chain (LCEL) using the ChatGroq model."""
    model = get_chat_model()
    system_message = FPL_GAFFER_SYSTEM_PROMPT

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    return prompt | model
