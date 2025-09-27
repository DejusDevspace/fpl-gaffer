from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from fpl_gaffer.utils.helpers import get_chat_model
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

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

class ResponseValidation(BaseModel):
    """Result from validating the response of FPL Gaffer to the user's prompt."""
    validation_passed: bool = Field(
        ...,
        description="Whether the response passes the validation test"
    )
    errors: List[str] = Field(
        ...,
        description="List of specific errors found, if any."
    )
    suggestions: List[str] = Field(
        ...,
        description="List of what should be fixed or looked into."
    )


def get_tools_chain(prompt_template: str):
    """Create a chain to analyze user message and return structured tool analysis output."""
    model = get_chat_model().with_structured_output(ToolAnalysis)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_template),
            MessagesPlaceholder(variable_name="messages")
        ]
    )

    return prompt | model

def get_gaffer_response_chain(prompt_template: str):
    """Create a response generation chain (LCEL) using the ChatGroq model."""
    model = get_chat_model()

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_template),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    return prompt | model

def get_response_validation_chain(prompt_template: str):
    model = get_chat_model().with_structured_output(ResponseValidation)

    prompt = ChatPromptTemplate.from_messages([("system", prompt_template)])

    return prompt | model
