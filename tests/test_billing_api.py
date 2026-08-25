import hashlib
import hmac
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fpl_gaffer.integrations.api.app.routes.billing import (
    CheckoutRequest,
    create_checkout,
    paystack_webhook,
    stripe_webhook,
)
from fpl_gaffer.integrations.api.main import app


class _FakeRequest:
    def __init__(self, body_bytes: bytes, headers: dict = None):
        self._body_bytes = body_bytes
        self.headers = headers or {}

    async def body(self) -> bytes:
        return self._body_bytes


class BillingApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_billing_routes_are_mounted_on_main_api(self):
        billing_routes = [route.path for route in app.routes if "billing" in route.path]
        self.assertIn("/billing/checkout", billing_routes)
        self.assertIn("/billing/webhooks/stripe", billing_routes)
        self.assertIn("/billing/webhooks/paystack", billing_routes)

    async def test_create_checkout_stripe_returns_checkout_url(self):
        fake_user = {"sub": "user-123", "email": "test@example.com"}
        with (
            patch("fpl_gaffer.integrations.api.app.routes.billing.settings.STRIPE_API_KEY", "sk_test_123"),
            patch(
                "fpl_gaffer.integrations.api.app.routes.billing.settings.STRIPE_BASIC_PRICE_ID", "price_123"
            ),
            patch("stripe.checkout.Session.create") as mock_session_create,
        ):
            mock_session = MagicMock()
            mock_session.url = "https://checkout.stripe.com/pay/cs_test_123"
            mock_session_create.return_value = mock_session

            response = await create_checkout(
                body=CheckoutRequest(tier="basic", provider="stripe"),
                current_user=fake_user,
            )

        self.assertEqual(response.checkout_url, "https://checkout.stripe.com/pay/cs_test_123")
        mock_session_create.assert_called_once()

    async def test_create_checkout_paystack_returns_checkout_url(self):
        fake_user = {"sub": "user-123", "email": "test@example.com"}
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = {
            "status": True,
            "data": {"authorization_url": "https://checkout.paystack.com/auth_code_123"},
        }
        mock_http_response.raise_for_status = MagicMock()

        with (
            patch(
                "fpl_gaffer.integrations.api.app.routes.billing.settings.PAYSTACK_SECRET_KEY",
                "sk_paystack_123",
            ),
            patch(
                "fpl_gaffer.integrations.api.app.routes.billing.settings.PAYSTACK_BASIC_PLAN_CODE", "PLN_123"
            ),
            patch(
                "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_http_response
            ) as mock_post,
        ):
            response = await create_checkout(
                body=CheckoutRequest(tier="basic", provider="paystack"),
                current_user=fake_user,
            )

        self.assertEqual(response.checkout_url, "https://checkout.paystack.com/auth_code_123")
        mock_post.assert_awaited_once()

    async def test_stripe_webhook_rejects_invalid_signature(self):
        with (
            patch(
                "fpl_gaffer.integrations.api.app.routes.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test"
            ),
            patch("stripe.Webhook.construct_event", side_effect=ValueError("Invalid signature")),
        ):
            fake_req = _FakeRequest(b"{}", headers={"stripe-signature": "invalid"})
            with self.assertRaises(Exception) as ctx:
                await stripe_webhook(fake_req)
            self.assertEqual(ctx.exception.status_code, 400)

    async def test_stripe_webhook_handles_checkout_session_completed(self):
        fake_event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": "user-123",
                    "customer": "cus_123",
                    "subscription": "sub_123",
                }
            },
        }

        with (
            patch(
                "fpl_gaffer.integrations.api.app.routes.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test"
            ),
            patch("stripe.Webhook.construct_event", return_value=fake_event),
            patch(
                "fpl_gaffer.integrations.api.app.routes.billing.database_service.upsert_subscription",
                new_callable=AsyncMock,
            ) as mock_upsert,
        ):
            fake_req = _FakeRequest(b"{}", headers={"stripe-signature": "valid"})
            res = await stripe_webhook(fake_req)

        self.assertEqual(res, {"received": True})
        mock_upsert.assert_awaited_once_with(
            user_id="user-123",
            tier="basic",
            status="active",
            provider="stripe",
            provider_customer_id="cus_123",
            provider_subscription_id="sub_123",
        )

    async def test_paystack_webhook_rejects_invalid_signature(self):
        with patch(
            "fpl_gaffer.integrations.api.app.routes.billing.settings.PAYSTACK_SECRET_KEY", "secret_123"
        ):
            fake_req = _FakeRequest(b'{"event":"test"}', headers={"x-paystack-signature": "invalid_sig"})
            with self.assertRaises(Exception) as ctx:
                await paystack_webhook(fake_req)
            self.assertEqual(ctx.exception.status_code, 400)

    async def test_paystack_webhook_handles_subscription_create(self):
        payload_dict = {
            "event": "subscription.create",
            "data": {
                "metadata": {"user_id": "user-456"},
                "customer": {"customer_code": "CUS_456"},
                "subscription_code": "SUB_456",
            },
        }
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        secret = "secret_123"
        valid_sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha512).hexdigest()

        with (
            patch("fpl_gaffer.integrations.api.app.routes.billing.settings.PAYSTACK_SECRET_KEY", secret),
            patch(
                "fpl_gaffer.integrations.api.app.routes.billing.database_service.upsert_subscription",
                new_callable=AsyncMock,
            ) as mock_upsert,
        ):
            fake_req = _FakeRequest(payload_bytes, headers={"x-paystack-signature": valid_sig})
            res = await paystack_webhook(fake_req)

        self.assertEqual(res, {"status": "success"})
        mock_upsert.assert_awaited_once_with(
            user_id="user-456",
            tier="basic",
            status="active",
            provider="paystack",
            provider_customer_id="CUS_456",
            provider_subscription_id="SUB_456",
        )


if __name__ == "__main__":
    unittest.main()
