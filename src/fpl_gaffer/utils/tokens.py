import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")


def estimate_message_tokens(messages) -> int:
    """Rough token estimate for a list of LangChain messages. Not exact for Groq's tokenizer,
    but consistent and cheap enough to gate a summarization trigger on."""
    total = 0
    for m in messages:
        content = m.content if isinstance(m.content, str) else str(m.content)
        total += len(_ENCODING.encode(content))
    return total
