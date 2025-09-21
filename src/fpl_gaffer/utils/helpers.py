from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq
from fpl_gaffer.tools.loader import TOOLS
from fpl_gaffer.settings import settings

def get_chat_model() -> ChatGroq:
    """Initialize and return a ChatGroq model instance."""
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL_NAME,
        temperature=settings.GROQ_MODEL_TEMPERATURE,
    )

def get_chat_model_with_tools() -> Runnable:
    """Initialize and return a ChatGroq model instance with tools."""
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL_NAME,
        temperature=settings.GROQ_MODEL_TEMPERATURE
    ).bind_tools(TOOLS)
