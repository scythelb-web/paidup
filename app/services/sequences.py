"""Follow-up engine — automated invoice reminder sequences."""

from app.config import FOLLOWUP_SEQUENCE

# Default email templates for each follow-up step
DEFAULT_TEMPLATES = {
    1: {
        "subject": "Quick reminder — invoice #{{invoice_number}}",
        "body": """<p>Hi {{customer_name}},</p>
<p>Just a friendly nudge that invoice <strong>#{{invoice_number}}</strong> for <strong>${{amount}}</strong> was due on {{due_date}}.</p>
<p>It might have slipped through the cracks — no worries! You can pay here:</p>
<p><a href="{{payment_link}}" style="display:inline-block;padding:12px 24px;background:#4F46E5;color:white;text-decoration:none;border-radius:6px;">
  Pay Invoice Now
</a></p>
<p>Thanks!<br>— {{business_name}}</p>"""
    },
    3: {
        "subject": "Following up — invoice #{{invoice_number}} is past due",
        "body": """<p>Hi {{customer_name}},</p>
<p>I wanted to follow up on invoice <strong>#{{invoice_number}}</strong> for <strong>${{amount}}</strong>, which is now a week past due.</p>
<p>If payment has already been sent, please disregard this message. Otherwise, you can settle it here:</p>
<p><a href="{{payment_link}}" style="display:inline-block;padding:12px 24px;background:#4F46E5;color:white;text-decoration:none;border-radius:6px;">
  Pay Invoice Now
</a></p>
<p>If there are any issues or questions, just reply to this email.</p>
<p>— {{business_name}}</p>"""
    },
    5: {
        "subject": "Final notice — invoice #{{invoice_number}} requires attention",
        "body": """<p>Hi {{customer_name}},</p>
<p>This is a final notice regarding invoice <strong>#{{invoice_number}}</strong> for <strong>${{amount}}</strong>, which is now 21 days past due.</p>
<p>If payment is not received within 7 days, a late fee of <strong>${{late_fee}}</strong> will be applied.</p>
<p><a href="{{payment_link}}" style="display:inline-block;padding:12px 24px;background:#DC2626;color:white;text-decoration:none;border-radius:6px;">
  Pay Now to Avoid Late Fee
</a></p>
<p>We'd really like to resolve this. Reply if you need to discuss payment options.</p>
<p>— {{business_name}}</p>"""
    },
    6: {
        "subject": "Invoice #{{invoice_number}} — collections warning",
        "body": """<p>Hi {{customer_name}},</p>
<p>Despite multiple reminders, invoice <strong>#{{invoice_number}}</strong> for <strong>${{amount}}</strong> remains unpaid — now 30 days past due.</p>
<p>This is our last attempt before escalating. Please pay immediately to avoid further action:</p>
<p><a href="{{payment_link}}" style="display:inline-block;padding:12px 24px;background:#DC2626;color:white;text-decoration:none;border-radius:6px;">
  Pay Immediately
</a></p>
<p>If you believe this is an error, contact us right away.</p>
<p>— {{business_name}}</p>"""
    },
}

# Generic templates for steps without specific copy (used as fallback)
_GENERIC_TEMPLATE = {
    "subject": "Reminder: invoice #{{invoice_number}}",
    "body": """<p>Hi {{customer_name}},</p>
<p>This is a reminder that invoice <strong>#{{invoice_number}}</strong> for <strong>${{amount}}</strong> is past due.</p>
<p><a href="{{payment_link}}">Pay Invoice</a></p>
<p>— {{business_name}}</p>"""
}


def get_template_for_step(step_number: int) -> dict:
    """Return the email template for a given follow-up step."""
    return DEFAULT_TEMPLATES.get(step_number, _GENERIC_TEMPLATE)


def get_full_sequence() -> list[dict]:
    """Return the default follow-up sequence."""
    return FOLLOWUP_SEQUENCE
