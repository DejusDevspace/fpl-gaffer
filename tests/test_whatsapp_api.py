import unittest
from unittest.mock import AsyncMock, patch

from fpl_gaffer.integrations.api.app.routes.whatsapp import (
    whatsapp_webhook,
    whatsapp_webhook_health,
)
from fpl_gaffer.integrations.api.app.services.whatsapp import WhatsAppService
from fpl_gaffer.integrations.api.main import app


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
                Body="Who should I captain?",
                From="whatsapp:+2347012345678",
                MessageSid="SM123",
                MessageType="text",
            )

        self.assertEqual(response.status_code, 200)
        message = process_message.call_args.args[0]
        self.assertEqual(message.message_body, "Who should I captain?")
        self.assertEqual(message.from_number, "+2347012345678")
        self.assertEqual(message.message_id, "SM123")
        send_message.assert_awaited_once_with("+2347012345678", "Captain Saka looks solid.")


if __name__ == "__main__":
    unittest.main()
