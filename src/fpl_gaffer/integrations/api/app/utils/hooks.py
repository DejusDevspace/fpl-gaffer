import asyncio
import time
from typing import Any, Callable

from fpl_gaffer.integrations.api.app.services.database import database_service


class LangGraphInstrument:
    """
    Decorator/hook to instrument LangGraph node execution.
    Captures per-node durations and logs to metrics.
    """

    @staticmethod
    def instrument_node(tool_name: str):
        """Decorator to wrap a LangGraph node and record its execution time."""

        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs) -> Any:
                start = time.time()
                result = (
                    await func(*args, **kwargs)
                    if asyncio.iscoroutinefunction(func)
                    else func(*args, **kwargs)
                )
                duration_ms = (time.time() - start) * 1000

                # If db session and request_id available in kwargs, log it
                db = kwargs.get("db")
                request_id = kwargs.get("request_id")

                if db and request_id:
                    await database_service.record_tool_usage(
                        db=db,
                        request_id=request_id,
                        tool_name=tool_name,
                        duration_ms=duration_ms,
                    )

                return result

            return wrapper

        return decorator
