from langchain_groq import ChatGroq
from fpl_gaffer.settings import settings

def get_chat_model() -> ChatGroq:
    """Initialize and return a ChatGroq model instance."""
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL_NAME,
        temperature=settings.GROQ_MODEL_TEMPERATURE,
    )
