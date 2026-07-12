from fastapi import APIRouter, Request
from fastapi.responses import Response

from fpl_gaffer.integrations.api.app.services.whatsapp import whatsapp_service
from fpl_gaffer.integrations.api.app.utils.logger import logger


router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.get("/whatsapp")
async def whatsapp_webhook_health() -> dict:
    """Lightweight health check for webhook configuration."""
    return {"status": "ok", "channel": "whatsapp"}


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request) -> Response:
    """Handle Twilio WhatsApp webhook events."""
    try:
        form = await request.form()
        form_data = {key: str(value) for key, value in form.items()}
        signature = request.headers.get("X-Twilio-Signature")

        if not whatsapp_service.validate_webhook_signature(
            url=str(request.url),
            form_data=form_data,
            signature=signature,
        ):
            return Response(content="Invalid Twilio signature", status_code=403)

        message = whatsapp_service.build_message(
            body=form_data.get("Body", ""),
            from_number=form_data.get("From", ""),
            message_id=form_data.get("MessageSid", ""),
            message_type=form_data.get("MessageType", "text"),
        )

        reply = await whatsapp_service.process_message(message)
        sent = await whatsapp_service.send_message(message.from_number, reply)

        if not sent:
            return Response(content="Failed to send WhatsApp reply", status_code=500)

        return Response(content="Message processed successfully", status_code=200)
    except Exception as exc:
        logger.error("Error processing WhatsApp webhook: %s", exc, exc_info=True)
        return Response(content="Internal server error", status_code=500)
