# PaidUp

Automated invoice follow-up for Stripe. Never chase an invoice again.

Connect your Stripe account → PaidUp watches for unpaid invoices → sends escalating email reminders → stops automatically when paid.

## Stack

- **Backend:** Python 3.12 + FastAPI
- **Database:** SQLite
- **Email:** SendGrid
- **Payments:** Stripe
- **Frontend:** Jinja2 templates

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 init_db.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | JWT signing key |
| `SENDGRID_API_KEY` | Yes | SendGrid API key for sending reminder emails |
| `BASE_URL` | Yes | Public URL (e.g. https://paidup.onrender.com) |
| `DATABASE_URL` | No | Database path (default: sqlite:///./paidup.db) |

## Deployment

Push to GitHub and connect to Render.com. `render.yaml` is pre-configured.
