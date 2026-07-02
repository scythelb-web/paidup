import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./paidup.db")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "scythelb@gmail.com")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Invoice follow-up sequence (days after invoice due date)
FOLLOWUP_SEQUENCE = [
    {"step": 1, "day": 1,  "channel": "email", "name": "Friendly nudge (day after due)"},
    {"step": 2, "day": 3,  "channel": "email", "name": "Gentle reminder"},
    {"step": 3, "day": 7,  "channel": "email", "name": "Firm follow-up"},
    {"step": 4, "day": 14, "channel": "email", "name": "Escalation notice"},
    {"step": 5, "day": 21, "channel": "email", "name": "Final notice with late fee warning"},
    {"step": 6, "day": 30, "channel": "email", "name": "Last attempt — collections warning"},
]
