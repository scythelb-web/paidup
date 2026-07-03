"""Email service — sends invoice reminders via SendGrid."""

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Subject, HtmlContent
from app.config import SENDGRID_API_KEY
import logging

logger = logging.getLogger(__name__)

_sg = None


def _get_sg():
    global _sg
    if _sg is None and SENDGRID_API_KEY:
        _sg = SendGridAPIClient(SENDGRID_API_KEY)
    return _sg


def send_reminder_email(
    to_email: str,
    to_name: str,
    subject: str,
    body_html: str,
) -> bool:
    """Send an invoice reminder email. Returns True if sent successfully."""
    sg = _get_sg()
    if not sg:
        logger.warning("SendGrid not configured — skipping email to %s", to_email)
        return False

    message = Mail(
        from_email=From("scythelb@gmail.com", "PaidUp Reminders"),
        to_emails=To(to_email, to_name),
        subject=Subject(subject),
        html_content=HtmlContent(body_html),
    )

    try:
        response = sg.send(message)
        ok = 200 <= response.status_code < 300
        if ok:
            logger.info("Reminder email sent to %s — status %d", to_email, response.status_code)
        else:
            logger.error("SendGrid error %d: %s", response.status_code, response.body)
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
    sg = _get_sg()
    if not sg:
        return {"sent": False, "error": "SendGrid not configured"}

    message = Mail(
        from_email=From("scythelb@gmail.com", "PaidUp Reminders"),
        to_emails=To(to_email, to_name),
        subject=Subject(subject),
        html_content=HtmlContent(body_html),
    )

    try:
        response = sg.send(message)
        return {
            "sent": 200 <= response.status_code < 300,
            "status_code": response.status_code,
            "body": str(response.body)[:500],
            "headers": dict(response.headers),
        }
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error("SendGrid send failed:\n%s", tb)
        return {"sent": False, "error": str(e), "traceback": tb[-2000:]}
