"""Stripe integration — direct API key management."""

import stripe
import httpx
import logging

logger = logging.getLogger(__name__)


def validate_stripe_key(api_key: str) -> bool:
    """Test whether a given Stripe secret key is valid."""
    try:
        resp = httpx.get(
            "https://api.stripe.com/v1/account",
            auth=(api_key, ""),
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def get_stripe_account_name(api_key: str) -> str | None:
    """Get the Stripe account's business name or email."""
    try:
        resp = httpx.get(
            "https://api.stripe.com/v1/account",
            auth=(api_key, ""),
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return (
                data.get("business_profile", {}).get("name")
                or data.get("settings", {}).get("dashboard", {}).get("display_name")
                or data.get("email", "")
            )
    except Exception:
        pass
    return None


def register_webhook(api_key: str, webhook_url: str) -> bool:
    """Register a webhook endpoint on the user's Stripe account."""
    try:
        stripe.WebhookEndpoint.create(
            url=webhook_url,
            enabled_events=[
                "invoice.created",
                "invoice.finalized",
                "invoice.payment_failed",
                "invoice.paid",
            ],
            api_key=api_key,
        )
        return True
    except Exception as e:
        logger.warning("Could not auto-register webhook: %s", e)
        return False
