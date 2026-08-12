import time
import tiktoken
from typing import Optional, Dict, Any
from langfuse import get_client

from fpl_gaffer.settings import settings
from fpl_gaffer.integrations.api.app.utils.logger import logger
from fpl_gaffer.graph.graph import graph
from fpl_gaffer.integrations.api.app.services.database import database_service

class AgentWrapper:
    def __init__(self):
        try:
            self.token_encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except:
            self.token_encoder = None

        self.langfuse_client = None

        if settings.LANGFUSE_ENABLED:
            try:

                self.langfuse_client = get_client(public_key=settings.LANGFUSE_API_KEY)
                logger.info("LangFuse client initialized")
            except ImportError:
                logger.warning("LangFuse SDK not available; using DB logging fallback")

    async def call_agent(
        self,
        prompt: str,
        user_id: Optional[str] = None,
        fpl_id: Optional[int] = None,
        session_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Orchestrate the LangGraph workflow and capture metrics."""
        meta = meta or {}
        request_id = meta.get("request_id", "unknown")
        start_time = time.time()

        # Resolve User Context
        if fpl_id is None and user_id:
            fpl_id = await database_service.get_fpl_id_by_user_id(user_id)
            if fpl_id is None:
                return {
                    "text": None,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "latency_ms": (time.time() - start_time) * 1000,
                    "cost_usd": 0.0,
                    "model": settings.GROQ_MODEL_NAME,
                    "status": "error",
                    "error": "Could not resolve an FPL ID for this user.",
                }

        # Prepare Graph Input
        # We use a message object for the graph state
        if fpl_id is None:
            if settings.DEBUG:
                fpl_id = settings.FPL_MANAGER_ID
            else:
                return {
                    "text": None,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "latency_ms": (time.time() - start_time) * 1000,
                    "cost_usd": 0.0,
                    "model": settings.GROQ_MODEL_NAME,
                    "status": "error",
                    "error": "No FPL ID available for this request.",
                }

        inputs = {
            "messages": [{"role": "user", "content": prompt}],
            "user_id": fpl_id,
            "is_retry": False,
            "retry_count": 0
        }

        # Invoke Graph with Thread Memory
        config = {"configurable": {"thread_id": session_id or "default"}}

        try:
            final_state = await graph.ainvoke(inputs, config=config)

            latency_ms = (time.time() - start_time) * 1000
            text = final_state.get("response", "The agent was unable to generate a response.")

            # Extract Metrics from state
            tokens_in = final_state.get("tokens_in", 0)
            tokens_out = final_state.get("tokens_out", 0)
            model = final_state.get("model", settings.GROQ_MODEL_NAME)

            # Fallback token estimation if graph didn't populate them
            if tokens_in == 0 and self.token_encoder:
                tokens_in = len(self.token_encoder.encode(prompt))
            if tokens_out == 0 and self.token_encoder:
                tokens_out = len(self.token_encoder.encode(text))

            total_tokens = tokens_in + tokens_out
            cost_usd = (total_tokens / 1000.0) * settings.MODEL_COST_PER_1K

            result = {
                "text": text,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency_ms": latency_ms,
                "cost_usd": cost_usd,
                "model": model,
                "status": "ok",
            }

            # Telemetry Persistence
            await database_service.create_request(
                user_id=user_id,
                route="chat",
                prompt=prompt,
                response=text,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                model=model,
                status="ok"
            )

            await self._send_to_langfuse(request_id, user_id, result, meta)

            logger.info(
                "Agent workflow successful",
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost_usd": cost_usd,
                    "latency_ms": latency_ms,
                }
            )

            return result

        except Exception as e:
            logger.error(f"Agent workflow failed: {str(e)}", extra={"request_id": request_id, "user_id": user_id})
            latency_ms = (time.time() - start_time) * 1000
            return {
                "text": None,
                "tokens_in": 0,
                "tokens_out": 0,
                "latency_ms": latency_ms,
                "cost_usd": 0.0,
                "model": settings.GROQ_MODEL_NAME,
                "status": "error",
                "error": str(e),
            }

    async def _send_to_langfuse(
        self,
        request_id: str,
        user_id: Optional[str],
        result: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> None:
        """Send metrics to LangFuse if available."""
        if not self.langfuse_client:
            return

        try:
            self.langfuse_client.trace(
                id=request_id,
                user_id=user_id,
                metadata={
                    "tokens_in": result["tokens_in"],
                    "tokens_out": result["tokens_out"],
                    "cost_usd": result["cost_usd"],
                    "latency_ms": result["latency_ms"],
                    "model": result["model"],
                    **meta,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send telemetry to LangFuse: {str(e)}")

agent_wrapper = AgentWrapper()
