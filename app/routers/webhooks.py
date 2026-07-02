"""Stripe webhook handler — watches invoices and triggers follow-ups."""

import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import RedirectResponse
from jinja2 import Template

from app.database import get_db
from app.services.sequences import get_template_for_step, get_full_sequence
from app.services.emailer import send_reminder_email
from app.config import BASE_URL
from app.templates import render

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stripe", tags=["stripe"])


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events from connected accounts."""
    payload = await request.body()

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid payload")

    event_type = event.get("type", "")
    logger.info("Webhook received: %s", event_type)

    obj = event.get("data", {}).get("object", {})

    if event_type == "invoice.payment_failed":
        await handle_invoice_payment_failed(obj)
    elif event_type in ("invoice.paid", "invoice.payment_succeeded"):
        await handle_invoice_paid(obj)
    elif event_type in ("invoice.created", "invoice.finalized"):
        await handle_invoice_created(obj)

    return {"status": "ok"}


async def handle_invoice_created(invoice: dict):
    """A new invoice was created or finalized — track it for follow-up."""
    invoice_id = invoice.get("id")
    stripe_customer_id = invoice.get("customer")
    customer_email = invoice.get("customer_email", "")
    customer_name = invoice.get("customer_name", customer_email)
    amount = invoice.get("amount_due", 0)
    currency = invoice.get("currency", "usd")
    due_date = invoice.get("due_date")
    status = invoice.get("status", "open")

    # Only track if it's an open invoice that will need follow-up
    if status not in ("open", "uncollectible"):
        return

    # Find which user this invoice belongs to via their Stripe API key
    # We track invoices by matching the Stripe account
    with get_db() as db:
        stripe_account = invoice.get("account_id") or invoice.get("metadata", {}).get("stripe_account", "")

        # Find user by Stripe account ID
        user_row = None
        if stripe_account:
            user_row = db.execute(
                "SELECT * FROM users WHERE stripe_account_id = ?",
                (stripe_account,),
            ).fetchone()

        if not user_row:
            # Try matching by customer email domain as fallback
            logger.info("No PaidUp user found for invoice %s", invoice_id)
            return

        user = dict(user_row)

        # Dedup — check if already tracked
        existing = db.execute(
            "SELECT id FROM unpaid_invoices WHERE stripe_invoice_id = ?",
            (invoice_id,),
        ).fetchone()

        if existing:
            return  # Already tracking

        db.execute(
            """INSERT INTO unpaid_invoices
               (user_id, stripe_invoice_id, stripe_customer_id, customer_email,
                customer_name, amount, currency, due_date, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user["id"], invoice_id, stripe_customer_id, customer_email,
             customer_name, amount, currency, due_date, status),
        )

        logger.info("Tracking new invoice %s for user %s", invoice_id, user["email"])


async def handle_invoice_payment_failed(invoice: dict):
    """An invoice payment failed — send the appropriate follow-up reminder."""
    invoice_id = invoice.get("id")
    amount = invoice.get("amount_due", 0)
    currency = invoice.get("currency", "usd")

    logger.info("Invoice payment failed: %s amount=%d", invoice_id, amount)

    with get_db() as db:
        inv = db.execute(
            "SELECT * FROM unpaid_invoices WHERE stripe_invoice_id = ?",
            (invoice_id,),
        ).fetchone()

        if not inv:
            logger.warning("Untracked invoice failed: %s", invoice_id)
            return

        invoice_row = dict(inv)
        user = dict(db.execute(
            "SELECT * FROM users WHERE id = ?", (invoice_row["user_id"],)
        ).fetchone())

        # Determine which step to send
        step = get_full_sequence()[0]  # Default: first step

        # Check how many reminders already sent
        sent_count = db.execute(
            "SELECT COUNT(*) as count FROM reminder_log WHERE unpaid_invoice_id = ?",
            (invoice_row["id"],),
        ).fetchone()["count"]

        step_index = min(sent_count, len(get_full_sequence()) - 1)
        step = get_full_sequence()[step_index]

        # Send the reminder
        await send_followup(db, user, invoice_row, step)

        # Update attempt count
        db.execute(
            "UPDATE unpaid_invoices SET attempt_count = ?, last_reminder_at = CURRENT_TIMESTAMP, status = 'overdue' WHERE id = ?",
            (sent_count + 1, invoice_row["id"]),
        )


async def handle_invoice_paid(invoice: dict):
    """An invoice was paid — mark it as collected."""
    invoice_id = invoice.get("id")
    amount = invoice.get("amount_paid", 0)

    logger.info("Invoice paid: %s amount=%d", invoice_id, amount)

    with get_db() as db:
        inv = db.execute(
            "SELECT * FROM unpaid_invoices WHERE stripe_invoice_id = ? AND status != 'collected'",
            (invoice_id,),
        ).fetchone()

        if not inv:
            return

        invoice_row = dict(inv)

        db.execute(
            """UPDATE unpaid_invoices
               SET status = 'collected', resolved_at = CURRENT_TIMESTAMP, resolved_status = 'collected'
               WHERE id = ?""",
            (invoice_row["id"],),
        )

        # Update stats
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        db.execute(
            """INSERT INTO collection_stats (user_id, month, total_invoices, total_collected,
               total_amount, total_amount_collected)
               VALUES (?, ?, 0, 1, 0, ?)
               ON CONFLICT(user_id, month) DO UPDATE SET
               total_collected = total_collected + 1,
               total_amount_collected = total_amount_collected + ?""",
            (invoice_row["user_id"], month, amount, amount),
        )


async def send_followup(db, user: dict, invoice: dict, step: dict):
    """Send a follow-up reminder for an unpaid invoice."""
    step_num = step["step"]
    template = get_template_for_step(step_num)

    customer_name = invoice.get("customer_name", "there")
    customer_email = invoice.get("customer_email", "")
    if not customer_email:
        logger.warning("No email for invoice %s — can't send reminder", invoice["stripe_invoice_id"])
        return

    business_name = user.get("stripe_account_name", user.get("email", ""))

    # Build payment link (Stripe hosted invoice page)
    payment_link = f"https://dashboard.stripe.com/invoices/{invoice['stripe_invoice_id']}"

    # Calculate late fee (10% of invoice amount, min $20)
    amount = invoice["amount"] / 100
    late_fee = max(amount * 0.1, 20)

    # Due date formatting
    due_date = invoice.get("due_date") or "N/A"
    if due_date and due_date != "N/A":
        try:
            dt = datetime.fromtimestamp(due_date) if isinstance(due_date, (int, float)) else datetime.fromisoformat(str(due_date).replace("Z", "+00:00"))
            due_date = dt.strftime("%B %d, %Y")
        except Exception:
            pass

    vars = {
        "customer_name": customer_name,
        "invoice_number": invoice["stripe_invoice_id"].replace("in_", ""),
        "amount": f"{amount:.2f}",
        "due_date": due_date,
        "payment_link": payment_link,
        "business_name": business_name,
        "late_fee": f"{late_fee:.2f}",
    }

    try:
        subject_tmpl = Template(template["subject"])
        body_tmpl = Template(template["body"])
        subject = subject_tmpl.render(**vars)
        body = body_tmpl.render(**vars)
    except Exception as e:
        logger.error("Template render error: %s", e)
        return

    sent = send_reminder_email(customer_email, customer_name, subject, body)

    # Log the reminder
    db.execute(
        """INSERT INTO reminder_log (unpaid_invoice_id, step_number, channel)
           VALUES (?, ?, 'email')""",
        (invoice["id"], step_num),
    )


@router.get("/setup")
async def setup_page(request: Request):
    """Show Stripe API key setup page."""
    from app.routers.auth import get_current_user
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    return render(request, "setup.html", {"user": user})


@router.post("/setup")
async def setup_save(request: Request, api_key: str = Form(...)):
    """Save and validate a Stripe API key."""
    from app.routers.auth import get_current_user
    from app.services.stripe import validate_stripe_key, get_stripe_account_name, register_webhook

    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    if not api_key.startswith("sk_"):
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            '<p style="color:red">Invalid key — must start with sk_</p><a href="/stripe/setup">Try again</a>',
            status_code=400,
        )

    if not validate_stripe_key(api_key):
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            '<p style="color:red">Invalid Stripe key — please double-check.</p><a href="/stripe/setup">Try again</a>',
            status_code=400,
        )

    # Get account info
    import httpx
    resp = httpx.get(
        "https://api.stripe.com/v1/account",
        auth=(api_key, ""),
        timeout=10,
    )
    acct = resp.json()
    stripe_account_id = acct.get("id", "")
    account_name = get_stripe_account_name(api_key)

    with get_db() as db:
        db.execute(
            "UPDATE users SET stripe_api_key = ?, stripe_account_id = ?, stripe_account_name = ?, setup_complete = 1 WHERE id = ?",
            (api_key, stripe_account_id, account_name, user["id"]),
        )

    # Register webhook
    register_webhook(api_key, f"{BASE_URL}/stripe/webhook")

    return RedirectResponse("/dashboard?setup=done", status_code=303)
