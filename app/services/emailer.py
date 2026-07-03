"""Email service — sends invoice reminders via SendGrid.

Uses httpx directly instead of the sendgrid library to avoid
python_http_client / urllib latin-1 encoding issues on Render.
"""
import json
import logging
import httpx
from app.config import SENDGRID_API_KEY

logger = logging.getLogger(__name__)

FROM_EMAIL = "scythelb@gmail.com"
FROM_NAME = "PaidUp Reminders"
SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


def _build_body(to_email: str, to_name: str, subject: str, body_html: str) -> dict:
    """Build the SendGrid v3 mail/send JSON body."""
    return {
        "from": {"email": FROM_EMAIL, "name": FROM_NAME},
        "subject": subject,
        "personalizations": [
            {
                "to": [{"email": to_email, "name": to_name}],
            }
        ],
        "content": [{"type": "text/html", "value": body_html}],
    }


def _send_sync(body: dict) -> httpx.Response:
    """Send a request to SendGrid and return the response."""
    return httpx.post(
        SENDGRID_URL,
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        },
        content=json.dumps(body),
        timeout=30,
    )


def send_reminder_email(
    to_email: str,
    to_name: str,
    subject: str,
    body_html: str,
) -> bool:
    """Send an invoice reminder email. Returns True if sent successfully."""
    if not SENDGRID_API_KEY:
        logger.warning("SendGrid not configured — skipping email to %s", to_email)
        return False

    body = _build_body(to_email, to_name, subject, body_html)

    try:
        response = _send_sync(body)
        ok = response.is_success
        if ok:
            logger.info("Reminder email sent to %s — status %d", to_email, response.status_code)
        else:
            logger.error("SendGrid error %d: %s", response.status_code, response.text[:500])
        return ok
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False


def send_reminder_email_debug(
    to_email: str,
    to_name: str,
    subject: str,
    body_html: str,
) -> dict:
    """Send email and return full debug info."""
    if not SENDGRID_API_KEY:
        return {"sent": False, "error": "SendGrid not configured"}

    body = _build_body(to_email, to_name, subject, body_html)

    try:
        response = _send_sync(body)
        return {
            "sent": response.is_success,
            "status_code": response.status_code,
            "body": response.text[:500],
            "headers": dict(response.headers),
        }
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error("SendGrid send failed:\n%s", tb)
        return {"sent": False, "error": str(e), "traceback": tb[-2000:]}
