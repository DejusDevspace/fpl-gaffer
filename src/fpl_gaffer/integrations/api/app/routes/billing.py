import hashlib
import hmac
import json
from typing import Optional

import httpx
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from fpl_gaffer.integrations.api.app.middleware.auth import require_auth
from fpl_gaffer.integrations.api.app.services.database import database_service
from fpl_gaffer.integrations.api.app.utils.logger import logger
from fpl_gaffer.settings import settings

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    tier: str = "basic"
    provider: str  # "stripe" | "paystack"


class CheckoutResponse(BaseModel):
    checkout_url: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    current_user: dict = Depends(require_auth),
):
    """Start a checkout flow for the authenticated user."""
    if body.tier != "basic":
        raise HTTPException(status_code=400, detail="Only 'basic' tier has an active price.")

    user_id = current_user.get("sub")
    user_email = current_user.get("email", "")

    if not user_id:
        raise HTTPException(status_code=401, detail="User ID unavailable from token claims")

    provider = body.provider.lower()

    if provider == "stripe":
        if not settings.STRIPE_API_KEY:
            raise HTTPException(status_code=500, detail="Stripe is not configured")
        if not settings.STRIPE_BASIC_PRICE_ID:
            raise HTTPException(status_code=500, detail="Stripe basic price ID is not configured")

        stripe.api_key = settings.STRIPE_API_KEY
        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": settings.STRIPE_BASIC_PRICE_ID, "quantity": 1}],
                client_reference_id=user_id,
                customer_email=user_email or None,
                success_url=f"{settings.ONBOARDING_URL}/billing/success"
                if settings.ONBOARDING_URL
                else "http://localhost:8000/billing/success",
                cancel_url=f"{settings.ONBOARDING_URL}/billing/cancel"
                if settings.ONBOARDING_URL
                else "http://localhost:8000/billing/cancel",
            )
            return CheckoutResponse(checkout_url=session.url)
        except Exception as exc:
            logger.error("Failed to create Stripe checkout session: %s", exc)
            raise HTTPException(status_code=500, detail=f"Stripe checkout failed: {str(exc)}")

    elif provider == "paystack":
        if not settings.PAYSTACK_SECRET_KEY:
            raise HTTPException(status_code=500, detail="Paystack is not configured")
        if not settings.PAYSTACK_BASIC_PLAN_CODE:
            raise HTTPException(status_code=500, detail="Paystack basic plan code is not configured")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.paystack.co/transaction/initialize",
                    headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
                    json={
                        "email": user_email or f"user_{user_id[:8]}@example.com",
                        "plan": settings.PAYSTACK_BASIC_PLAN_CODE,
                        "metadata": {"user_id": user_id},
                    },
                )
                response.raise_for_status()
                data = response.json().get("data", {})
                auth_url = data.get("authorization_url")
                if not auth_url:
                    raise ValueError("No authorization_url in Paystack response")
                return CheckoutResponse(checkout_url=auth_url)
        except Exception as exc:
            logger.error("Failed to create Paystack checkout: %s", exc)
            raise HTTPException(status_code=500, detail=f"Paystack checkout failed: {str(exc)}")

    raise HTTPException(status_code=400, detail=f"Unsupported provider: '{body.provider}'")


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET is not configured")
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")

    stripe.api_key = settings.STRIPE_API_KEY
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        logger.warning("Invalid Stripe webhook signature: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    event_type = event.get("type")
    obj = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        user_id = obj.get("client_reference_id")
        customer_id = obj.get("customer")
        subscription_id = obj.get("subscription")
        if user_id and customer_id and subscription_id:
            await database_service.upsert_subscription(
                user_id=user_id,
                tier="basic",
                status="active",
                provider="stripe",
                provider_customer_id=str(customer_id),
                provider_subscription_id=str(subscription_id),
            )
            logger.info("Stripe subscription created for user %s", user_id)

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        customer_id = str(obj.get("customer"))
        subscription_id = str(obj.get("id"))
        status = str(obj.get("status", "canceled"))
        period_end = obj.get("current_period_end")
        period_end_iso: Optional[str] = None
        if period_end:
            from datetime import datetime, timezone

            period_end_iso = datetime.fromtimestamp(period_end, tz=timezone.utc).isoformat()

        user_row = await database_service.get_user_by_provider_customer_id("stripe", customer_id)
        if user_row:
            await database_service.upsert_subscription(
                user_id=user_row["user_id"],
                tier="basic",
                status=status,
                provider="stripe",
                provider_customer_id=customer_id,
                provider_subscription_id=subscription_id,
                current_period_end=period_end_iso,
            )
            logger.info("Stripe subscription updated for user %s to status %s", user_row["user_id"], status)
        else:
            logger.warning("Stripe webhook received for unknown customer %s", customer_id)

    return {"received": True}


@router.post("/webhooks/paystack")
async def paystack_webhook(request: Request):
    """Handle Paystack webhook events."""
    payload = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    if not settings.PAYSTACK_SECRET_KEY:
        logger.error("PAYSTACK_SECRET_KEY is not configured")
        raise HTTPException(status_code=500, detail="Paystack secret key not configured")

    expected = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), payload, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(expected, signature):
        logger.warning("Invalid Paystack webhook signature")
        raise HTTPException(status_code=400, detail="Invalid Paystack signature")

    try:
        event = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}")

    event_type = event.get("event")
    data = event.get("data", {})

    if event_type == "subscription.create":
        user_id = data.get("metadata", {}).get("user_id")
        customer_code = data.get("customer", {}).get("customer_code")
        subscription_code = data.get("subscription_code")

        if user_id and customer_code and subscription_code:
            await database_service.upsert_subscription(
                user_id=user_id,
                tier="basic",
                status="active",
                provider="paystack",
                provider_customer_id=str(customer_code),
                provider_subscription_id=str(subscription_code),
            )
            logger.info("Paystack subscription created for user %s", user_id)

    elif event_type in ("subscription.disable", "subscription.not_renew"):
        customer_code = str(data.get("customer", {}).get("customer_code"))
        subscription_code = str(data.get("subscription_code"))
        status = "canceled" if event_type == "subscription.disable" else "active"

        user_row = await database_service.get_user_by_provider_customer_id("paystack", customer_code)
        if user_row:
            await database_service.upsert_subscription(
                user_id=user_row["user_id"],
                tier="basic",
                status=status,
                provider="paystack",
                provider_customer_id=customer_code,
                provider_subscription_id=subscription_code,
            )
            logger.info(
                "Paystack subscription status updated for user %s to status %s", user_row["user_id"], status
            )
        else:
            logger.warning("Paystack webhook received for unknown customer %s", customer_code)

    return {"status": "success"}
