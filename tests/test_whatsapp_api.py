import unittest
from unittest.mock import AsyncMock, patch

from fpl_gaffer.integrations.api.app.routes.whatsapp import (
    whatsapp_webhook,
    whatsapp_webhook_health,
)
from fpl_gaffer.integrations.api.app.services.whatsapp import (
    DEFAULT_LINK_FPL_RESPONSE,
    DEFAULT_REGISTRATION_RESPONSE,
    WhatsAppService,
)
from fpl_gaffer.integrations.api.main import app
from fpl_gaffer.integrations.whatsapp.schema import WhatsAppMessage


class _FakeRequest:
    def __init__(self, form_data, signature="valid-signature"):
        self._form_data = form_data
        self.headers = {"X-Twilio-Signature": signature}
        self.url = "https://api.example.com/api/webhooks/whatsapp"

    async def form(self):
        return self._form_data


class WhatsAppApiTests(unittest.IsolatedAsyncioTestCase):
    def test_normalize_number_removes_twilio_prefix(self):
        self.assertEqual(
            WhatsAppService.normalize_number("whatsapp:+2347012345678"),
            "+2347012345678",
        )

    async def test_whatsapp_health_route_returns_status(self):
        response = await whatsapp_webhook_health()

        self.assertEqual(response, {"status": "ok", "channel": "whatsapp"})

    async def test_whatsapp_routes_are_mounted_on_main_api(self):
        whatsapp_routes = [route.path for route in app.routes if "whatsapp" in route.path]

        self.assertEqual(whatsapp_routes.count("/api/webhooks/whatsapp"), 2)

    async def test_whatsapp_webhook_processes_and_replies_to_sender(self):
        with (
            patch(
                "fpl_gaffer.integrations.api.app.routes.whatsapp.whatsapp_service.validate_webhook_signature",
                return_value=True,
            ) as validate_signature,
            patch(
                "fpl_gaffer.integrations.api.app.routes.whatsapp.whatsapp_service.process_message",
                new_callable=AsyncMock,
                return_value="Captain Saka looks solid.",
            ) as process_message,
            patch(
                "fpl_gaffer.integrations.api.app.routes.whatsapp.whatsapp_service.send_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as send_message,
        ):
            response = await whatsapp_webhook(
                _FakeRequest(
                    {
                        "Body": "Who should I captain?",
                        "From": "whatsapp:+2347012345678",
                        "MessageSid": "SM123",
                        "MessageType": "text",
                    }
                )
            )

        self.assertEqual(response.status_code, 200)
        validate_signature.assert_called_once()
        message = process_message.call_args.args[0]
        self.assertEqual(message.message_body, "Who should I captain?")
        self.assertEqual(message.from_number, "+2347012345678")
        self.assertEqual(message.message_id, "SM123")
        send_message.assert_awaited_once_with("+2347012345678", "Captain Saka looks solid.")

    async def test_whatsapp_webhook_rejects_invalid_signature(self):
        with (
            patch(
                "fpl_gaffer.integrations.api.app.routes.whatsapp.whatsapp_service.validate_webhook_signature",
                return_value=False,
            ),
            patch(
                "fpl_gaffer.integrations.api.app.routes.whatsapp.whatsapp_service.process_message",
                new_callable=AsyncMock,
            ) as process_message,
            patch(
                "fpl_gaffer.integrations.api.app.routes.whatsapp.whatsapp_service.send_message",
                new_callable=AsyncMock,
            ) as send_message,
        ):
            response = await whatsapp_webhook(
                _FakeRequest(
                    {
                        "Body": "Who should I captain?",
                        "From": "whatsapp:+2347012345678",
                    },
                    signature="bad-signature",
                )
            )

        self.assertEqual(response.status_code, 403)
        process_message.assert_not_awaited()
        send_message.assert_not_awaited()

    async def test_unregistered_sender_gets_registration_prompt(self):
        service = WhatsAppService()
        message = WhatsAppMessage(
            message_type="text",
            from_number="+2347012345678",
            message_body="Rate my team",
            message_id="SM123",
        )

        with (
            patch(
                "fpl_gaffer.integrations.api.app.services.whatsapp.database_service.get_user_with_fpl_by_phone",
                new_callable=AsyncMock,
                return_value=None,
            ) as lookup,
            patch(
                "fpl_gaffer.integrations.api.app.services.whatsapp.agent_wrapper.call_agent",
                new_callable=AsyncMock,
            ) as call_agent,
        ):
            response = await service.process_message(message)

        self.assertEqual(response, DEFAULT_REGISTRATION_RESPONSE)
        lookup.assert_awaited_once_with("+2347012345678")
        call_agent.assert_not_awaited()

    async def test_registered_sender_without_fpl_id_gets_link_prompt(self):
        service = WhatsAppService()
        message = WhatsAppMessage(
            message_type="text",
            from_number="+2347012345678",
            message_body="Rate my team",
            message_id="SM123",
        )

        with (
            patch(
                "fpl_gaffer.integrations.api.app.services.whatsapp.database_service.get_user_with_fpl_by_phone",
                new_callable=AsyncMock,
                return_value={"user_id": "user-1", "phone": "+2347012345678", "fpl_id": None},
            ),
            patch(
                "fpl_gaffer.integrations.api.app.services.whatsapp.agent_wrapper.call_agent",
                new_callable=AsyncMock,
            ) as call_agent,
        ):
            response = await service.process_message(message)

        self.assertEqual(response, DEFAULT_LINK_FPL_RESPONSE)
        call_agent.assert_not_awaited()

    async def test_registered_sender_with_fpl_id_invokes_agent(self):
        service = WhatsAppService()
        message = WhatsAppMessage(
            message_type="text",
            from_number="+2347012345678",
            message_body="Rate my team",
            message_id="SM123",
        )

        with (
            patch(
                "fpl_gaffer.integrations.api.app.services.whatsapp.database_service.get_user_with_fpl_by_phone",
                new_callable=AsyncMock,
                return_value={"user_id": "user-1", "phone": "+2347012345678", "fpl_id": 12345},
            ),
            patch(
                "fpl_gaffer.integrations.api.app.services.whatsapp.agent_wrapper.call_agent",
                new_callable=AsyncMock,
                return_value={"status": "ok", "text": "Your team looks strong."},
            ) as call_agent,
        ):
            response = await service.process_message(message)

        self.assertEqual(response, "Your team looks strong.")
        call_agent.assert_awaited_once()
        kwargs = call_agent.call_args.kwargs
        self.assertEqual(kwargs["prompt"], "Rate my team")
        self.assertEqual(kwargs["user_id"], "user-1")
        self.assertEqual(kwargs["fpl_id"], 12345)
        self.assertEqual(kwargs["session_id"], "whatsapp:+2347012345678")


if __name__ == "__main__":
    unittest.main()
