"""PaidUp — Automated invoice follow-up for Stripe. Never chase an invoice again."""

import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.database import init_db
from app.routers import auth, webhooks, dashboard
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
        subject="PaidUp Email Test — It Works!",
        body_html="""<h2>Your PaidUp invoice reminders are configured!</h2>
        <p>This confirms that SendGrid is wired up and sending correctly.</p>
        <p>Your customers will now receive automated invoice follow-ups.</p>
        <p style="color:#888;font-size:12px;">Sent from PaidUp -- automated invoice follow-up</p>""",
    )
    return {"status": "ok" if result.get("sent") else "error", **result, "to": ADMIN_EMAIL}
