from fastapi import APIRouter, Form
from fastapi.responses import Response

from fpl_gaffer.integrations.api.app.services.whatsapp import whatsapp_service
from fpl_gaffer.integrations.api.app.utils.logger import logger


router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.get("/whatsapp")
async def whatsapp_webhook_health() -> dict:
    """Lightweight health check for webhook configuration."""
    return {"status": "ok", "channel": "whatsapp"}


@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(default=""),
    From: str = Form(default=""),
    MessageSid: str = Form(default=""),
    MessageType: str = Form(default="text"),
) -> Response:
    """Handle Twilio WhatsApp webhook events."""
    try:
        message = whatsapp_service.build_message(
            body=Body,
            from_number=From,
            message_id=MessageSid,
            message_type=MessageType,
        )

        reply = await whatsapp_service.process_message(message)
        sent = await whatsapp_service.send_message(message.from_number, reply)

        if not sent:
            return Response(content="Failed to send WhatsApp reply", status_code=500)

        return Response(content="Message processed successfully", status_code=200)
    except Exception as exc:
        logger.error("Error processing WhatsApp webhook: %s", exc, exc_info=True)
        return Response(content="Internal server error", status_code=500)
