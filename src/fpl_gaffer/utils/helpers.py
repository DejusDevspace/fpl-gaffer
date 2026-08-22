import logging
from typing import Any

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
            use_responses_api=True,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: '{provider}'. Supported providers: 'groq', 'openai'.")


def extract_message_text(content: Any) -> str:
    """Extract plain string text from a message content field (str, list of blocks, or dict)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "text" and "text" in block:
                    parts.append(str(block["text"]))
                elif "text" in block:
                    parts.append(str(block["text"]))
        return "\n".join(parts) if parts else str(content)
    if isinstance(content, dict):
        if content.get("type") == "text" and "text" in content:
            return str(content["text"])
        if "text" in content:
            return str(content["text"])
    return str(content) if content is not None else ""
