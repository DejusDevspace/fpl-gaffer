from fpl_gaffer.utils.helpers import get_chat_model
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from fpl_gaffer.core.prompts import FPL_GAFFER_SYSTEM_PROMPT

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
