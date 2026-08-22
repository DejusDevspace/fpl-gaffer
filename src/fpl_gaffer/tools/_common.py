import logging
from typing import Dict


def tool_error(logger: logging.Logger, context: str, exc: Exception) -> Dict:
    """Log the real exception for debugging; return a generic, user-safe shape for the model.
    Never pass raw exception text (URLs, status codes, stack fragments) into model context -
    that's exactly what ends up getting paraphrased straight back to the user. The model only
    ever needs to know that this particular lookup didn't work, not why."""
    logger.error("%s failed: %s", context, exc, exc_info=True)
    return {"error": "unavailable"}
