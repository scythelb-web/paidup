"""Billing routes — subscription plans and Stripe Checkout."""

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from app.templates import render
from app.routers.auth import get_current_user
from app.config import STRIPE_SECRET_KEY, BASE_URL
from app.database import get_db

router = APIRouter(prefix="/billing", tags=["billing"])

PRICE_IDS = {
    "starter": "price_REPLACE_paidup_starter",
    "growth": "price_REPLACE_paidup_growth",
    "scale": "price_REPLACE_paidup_scale",
}


@router.get("/pricing")
async def pricing_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    return render(request, "pricing.html", {"user": user, "selected": None})


@router.post("/checkout")
async def create_checkout(request: Request, plan: str = Form(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    if plan not in PRICE_IDS:
        return render(request, "pricing.html", {"user": user, "selected": plan, "error": "Invalid plan selected"})

    import stripe as _stripe
    _stripe.api_key = STRIPE_SECRET_KEY

    with get_db() as db:
        stripe_customer_id = user.get("stripe_customer_id")

        if not stripe_customer_id:
            customer = _stripe.Customer.create(
                email=user["email"],
                metadata={"user_id": str(user["id"])},
            )
            stripe_customer_id = customer.id
            db.execute(
                "UPDATE users SET stripe_customer_id = ? WHERE id = ?",
                (stripe_customer_id, user["id"]),
            )

    try:
        session = _stripe.checkout.Session.create(
            customer=stripe_customer_id,
            mode="subscription",
            line_items=[{"price": PRICE_IDS[plan], "quantity": 1}],
            success_url=f"{BASE_URL}/dashboard?checkout=success",
            cancel_url=f"{BASE_URL}/billing/pricing?cancelled=1",
            metadata={"user_id": str(user["id"])},
        )
        return RedirectResponse(session.url, status_code=303)
    except Exception as e:
        return render(request, "pricing.html", {"user": user, "selected": plan, "error": str(e)})


@router.get("/portal")
async def customer_portal(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    stripe_customer_id = user.get("stripe_customer_id")
    if not stripe_customer_id:
        return RedirectResponse("/billing/pricing", status_code=303)

    import stripe as _stripe
    _stripe.api_key = STRIPE_SECRET_KEY

    try:
        session = _stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=f"{BASE_URL}/billing/pricing",
        )
        return RedirectResponse(session.url, status_code=303)
    except Exception as e:
        return render(request, "pricing.html", {"user": user, "selected": None, "error": str(e)})
