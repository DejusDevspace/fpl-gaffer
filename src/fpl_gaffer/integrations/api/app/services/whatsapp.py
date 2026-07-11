from typing import Optional

from twilio.rest import Client

from fpl_gaffer.integrations.api.app.services.agent_wrapper import agent_wrapper
from fpl_gaffer.integrations.api.app.services.database import database_service
from fpl_gaffer.integrations.api.app.utils.logger import logger
from fpl_gaffer.integrations.api.app.utils.phone import normalize_phone_number
from fpl_gaffer.integrations.whatsapp.schema import WhatsAppMessage
from fpl_gaffer.settings import settings


UNSUPPORTED_MEDIA_RESPONSE = (
    "FPL Gaffer can only process text messages for now. Send your FPL question as text."
)
DEFAULT_REGISTRATION_RESPONSE = (
    "You're not set up on FPL Gaffer yet. Register with your name, WhatsApp number, "
    "and FPL ID first, then message me here again."
)
DEFAULT_LINK_FPL_RESPONSE = (
    "I found your WhatsApp number, but no FPL ID is linked yet. Link your FPL ID first, "
    "then message me here again."
)


class WhatsAppService:
    """WhatsApp channel adapter for Twilio webhook payloads."""

    def __init__(self):
        self._twilio_client: Optional[Client] = None

    @property
    def twilio_client(self) -> Client | None:
        if self._twilio_client is None:
            self._twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        return self._twilio_client

    @staticmethod
    def normalize_number(number: Optional[str]) -> str:
        """Normalize Twilio WhatsApp numbers into E.164-like phone strings."""
        return normalize_phone_number(number)

    def build_message(
        self,
        body: Optional[str],
        from_number: Optional[str],
        message_id: Optional[str],
        message_type: Optional[str] = None,
    ) -> WhatsAppMessage:
        normalized_from = self.normalize_number(from_number)
        return WhatsAppMessage(
            message_type=message_type or "text",
            from_number=normalized_from,
            message_body=body or "",
            message_id=message_id or "",
        )

    async def process_message(self, message: WhatsAppMessage) -> str:
        """Invoke the agent for a WhatsApp text message."""
        if message.message_type in {"audio", "image", "video", "document"}:
            return UNSUPPORTED_MEDIA_RESPONSE

        if not message.message_body.strip():
            return "Send me an FPL question and I'll take a look."

        user_context = await database_service.get_user_with_fpl_by_phone(message.from_number)
        if not user_context:
            return self.registration_prompt()

        if not user_context.get("fpl_id"):
            return self.link_fpl_prompt()

        result = await agent_wrapper.call_agent(
            prompt=message.message_body,
            user_id=user_context["user_id"],
            fpl_id=user_context["fpl_id"],
            session_id=f"whatsapp:{message.from_number}",
            meta={
                "route": "/api/webhooks/whatsapp",
                "channel": "whatsapp",
                "message_id": message.message_id,
                "from_number": message.from_number,
                "fpl_id": user_context["fpl_id"],
            },
        )

        if result["status"] == "error":
            logger.error(
                "WhatsApp agent invocation failed",
                extra={"message_id": message.message_id},
            )
            return "I couldn't process that just now. Please try again shortly."

        return result["text"]

    @staticmethod
    def registration_prompt() -> str:
        if settings.ONBOARDING_URL:
            return f"{DEFAULT_REGISTRATION_RESPONSE}\n\nRegister here: {settings.ONBOARDING_URL}"
        return DEFAULT_REGISTRATION_RESPONSE

    @staticmethod
    def link_fpl_prompt() -> str:
        if settings.ONBOARDING_URL:
            return f"{DEFAULT_LINK_FPL_RESPONSE}\n\nLink it here: {settings.ONBOARDING_URL}"
        return DEFAULT_LINK_FPL_RESPONSE

    async def send_message(self, to_number: str, message: str) -> bool:
        """Send a WhatsApp text message through Twilio."""
        try:
            response = self.twilio_client.messages.create(
                from_=f"whatsapp:{settings.TWILIO_NUMBER}",
                body=message,
                to=f"whatsapp:{self.normalize_number(to_number)}",
            )
            logger.info("WhatsApp message sent", extra={"message_id": response.sid})
            return True
        except Exception as exc:
            logger.error("Failed to send WhatsApp message: %s", exc)
            return False


whatsapp_service = WhatsAppService()
