import logging

from langchain_core.language_models.chat_models import BaseChatModel

from fpl_gaffer.settings import settings

logger = logging.getLogger(__name__)


def get_chat_model() -> BaseChatModel:
    """Return a chat model instance based on the configured LLM_PROVIDER.

    Switching providers requires only changing env vars:
        LLM_PROVIDER  — "groq" | "openai"
        LLM_MODEL     — e.g. "llama-3.3-70b-versatile" or "gpt-4o-mini"
        <PROVIDER>_API_KEY — the active provider's key
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: '{provider}'. Supported providers: 'groq', 'openai'.")
