from typing import List

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field

from fpl_gaffer.tools import TOOLS
from fpl_gaffer.utils.helpers import get_chat_model


class ResponseValidation(BaseModel):
    """Result from validating the response of FPL Gaffer to the user's prompt."""

    validation_passed: bool = Field(..., description="Whether the response passes the validation test")
    errors: List[str] = Field(..., description="List of specific errors found, if any.")
    suggestions: List[str] = Field(..., description="List of what should be fixed or looked into.")


def get_agent_chain(prompt_template: str, bind_tools: bool = True):
    """Create the main agent chain: system prompt + conversation history, with tools bound via
    native function-calling. The model decides whether to call tools, which ones, and with what
    arguments — it may return zero, one, or several tool calls in a single response.

    When bind_tools is False (e.g. tool-call budget exhausted), the model is returned without
    tools bound, forcing it to produce a content-only answer."""
    model = get_chat_model()
    if bind_tools:
        model = model.bind_tools(TOOLS)

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
