import logging
from fastapi import APIRouter, Request, Response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.api_route("/webhook/whatsapp/response", methods=["GET", "POST"])
async def whatsapp_webhook(request: Request) -> Response:
    """Endpoint to handle WhatsApp webhook events."""
    pass
