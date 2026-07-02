import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent.parent / "paidup.db"


def _connect():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                stripe_customer_id TEXT,
                plan TEXT DEFAULT 'free',
                stripe_api_key TEXT,
                stripe_account_id TEXT,
                stripe_account_name TEXT,
                setup_complete INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS unpaid_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                stripe_invoice_id TEXT UNIQUE NOT NULL,
                stripe_customer_id TEXT,
                customer_email TEXT,
                customer_name TEXT,
                amount INTEGER NOT NULL,
                currency TEXT DEFAULT 'usd',
                due_date TIMESTAMP,
                status TEXT DEFAULT 'open',
                attempt_count INTEGER DEFAULT 1,
                last_reminder_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolved_status TEXT
            );

            CREATE TABLE IF NOT EXISTS reminder_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unpaid_invoice_id INTEGER NOT NULL REFERENCES unpaid_invoices(id),
                step_number INTEGER NOT NULL,
                channel TEXT NOT NULL DEFAULT 'email',
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                opened INTEGER DEFAULT 0,
                clicked INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sequence_custom (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                step_number INTEGER NOT NULL,
                day INTEGER NOT NULL,
                channel TEXT DEFAULT 'email',
                subject TEXT,
                body_html TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS collection_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                month TEXT NOT NULL,
                total_invoices INTEGER DEFAULT 0,
                total_collected INTEGER DEFAULT 0,
                total_amount INTEGER DEFAULT 0,
                total_amount_collected INTEGER DEFAULT 0,
                UNIQUE(user_id, month)
            );
        """)
