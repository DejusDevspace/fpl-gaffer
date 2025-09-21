from pydantic import BaseModel, Field
from typing import List
from fpl_gaffer.utils.helpers import get_chat_model
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from fpl_gaffer.core.prompts import FPL_GAFFER_SYSTEM_PROMPT, TOOL_ANALYSIS_PROMPT

class ToolResponse(BaseModel):
    tools_to_call: List[str] = Field(..., description="The list of tools to call")


# TODO: Re-assess the get tools chain function
def get_tools_chain():
    """"""
    model = get_chat_model().with_structured_output(ToolResponse)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", TOOL_ANALYSIS_PROMPT),
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
