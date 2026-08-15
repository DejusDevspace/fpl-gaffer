from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from fpl_gaffer.integrations.api.app.middleware.auth import get_current_user
from fpl_gaffer.integrations.api.app.services.agent_wrapper import agent_wrapper
from fpl_gaffer.integrations.api.app.utils.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: Optional[dict] = Depends(get_current_user),
):
    """Chat endpoint with optional authentication."""
    request_id = str(uuid4())
    user_id = current_user.get("sub") if current_user else None

    # Call agent wrapper (which now handles graph invocation and metrics logging)
    result = await agent_wrapper.call_agent(
        prompt=request.message,
        user_id=user_id,
        session_id=request.session_id,
        meta={
            "request_id": request_id,
            "route": "/api/chat",
        },
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error", "LLM call failed"))

    return ChatResponse(
        reply=result["text"],
        request_id=request_id,
    )
