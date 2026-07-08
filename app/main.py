"""PaidUp — Automated invoice follow-up for Stripe. Never chase an invoice again."""

import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.database import init_db
from app.routers import auth, webhooks, dashboard, billing
from app.templates import render

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PaidUp", version="0.1.0")

# Static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Routers
app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(dashboard.router)
app.include_router(billing.router)


@app.on_event("startup")
async def startup():
    init_db()
    logger.info("PaidUp started")


@app.get("/")
async def landing(request: Request):
    return render(request, "landing.html")


@app.get("/health")
async def health():
    from app.config import SENDGRID_API_KEY
    return {
        "status": "ok",
        "service": "PaidUp",
        "sendgrid_configured": bool(SENDGRID_API_KEY),
        "version": "4309ec8",
    }


@app.post("/test-email")
async def test_email():
    """Send a test email to verify SendGrid is configured."""
    from app.config import SENDGRID_API_KEY, ADMIN_EMAIL
    from app.services.emailer import send_reminder_email_debug

    if not SENDGRID_API_KEY:
        return {"status": "error", "message": "SendGrid API key not configured"}

    result = send_reminder_email_debug(
        to_email=ADMIN_EMAIL,
        to_name="PaidUp User",
        subject="PaidUp Email Test",
        body_html="<p>Test email from PaidUp.</p>",
    )
    return {"status": "ok" if result.get("sent") else "error", **result, "to": ADMIN_EMAIL}


@app.get("/debug-api-key")
async def debug_api_key():
    """Diagnose the SENDGRID_API_KEY for encoding issues."""
    from app.config import SENDGRID_API_KEY
    key = SENDGRID_API_KEY or ""
    # Check for non-ASCII chars
    non_ascii = []
    for i, ch in enumerate(key):
        if ord(ch) > 127:
            non_ascii.append({"position": i, "char": ch, "ordinal": ord(ch)})
    return {
        "key_length": len(key),
        "key_prefix": key[:10] + "..." if len(key) > 10 else key,
        "all_ascii": all(ord(c) < 128 for c in key),
        "non_ascii_chars": non_ascii,
        "repr_first_50": repr(key[:50]),
    }


@app.post("/test-email-direct")
async def test_email_direct():
    """Send email via httpx directly — bypass sendgrid library."""
    from app.config import SENDGRID_API_KEY, ADMIN_EMAIL
    import httpx
    import json

    if not SENDGRID_API_KEY:
        return {"status": "error", "message": "SendGrid API key not configured"}

    body = {
        "from": {"email": "scythelb@gmail.com", "name": "PaidUp Reminders"},
        "subject": "PaidUp Direct Test",
        "personalizations": [{"to": [{"email": ADMIN_EMAIL, "name": "PaidUp User"}]}],
        "content": [{"type": "text/html", "value": "<p>Test email from PaidUp (direct httpx).</p>"}],
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                content=json.dumps(body),
            )
        return {
            "sent": resp.is_success,
            "status_code": resp.status_code,
            "body": resp.text[:500],
        }
    except Exception as e:
        import traceback
        return {"sent": False, "error": str(e), "traceback": traceback.format_exc()[-2000:]}
