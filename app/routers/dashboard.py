"""Dashboard routes — main customer interface."""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.routers.auth import get_current_user
from app.database import get_db
from datetime import datetime, timezone
from app.templates import render

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    with get_db() as db:
        # Active overdue invoices
        active_count = db.execute(
            "SELECT COUNT(*) as count FROM unpaid_invoices WHERE user_id = ? AND status = 'overdue'",
            (user["id"],),
        ).fetchone()["count"]

        open_count = db.execute(
            "SELECT COUNT(*) as count FROM unpaid_invoices WHERE user_id = ? AND status = 'open'",
            (user["id"],),
        ).fetchone()["count"]

        # This month's stats
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        month_stats = db.execute(
            """SELECT total_invoices, total_collected, total_amount, total_amount_collected
               FROM collection_stats WHERE user_id = ? AND month = ?""",
            (user["id"], month),
        ).fetchone()

        # All-time
        all_time = db.execute(
            """SELECT
                 COALESCE(SUM(total_invoices), 0) as invoices,
                 COALESCE(SUM(total_collected), 0) as collected,
                 COALESCE(SUM(total_amount), 0) as amount_total,
                 COALESCE(SUM(total_amount_collected), 0) as amount_collected
               FROM collection_stats WHERE user_id = ?""",
            (user["id"],),
        ).fetchone()

        # Recent unpaid invoices
        recent = db.execute(
            """SELECT ui.*, 
                 (SELECT COUNT(*) FROM reminder_log rl WHERE rl.unpaid_invoice_id = ui.id) as reminders_sent
               FROM unpaid_invoices ui
               WHERE ui.user_id = ? AND ui.status IN ('open', 'overdue')
               ORDER BY ui.created_at DESC LIMIT 20""",
            (user["id"],),
        ).fetchall()

        # Recently collected
        collected = db.execute(
            """SELECT ui.*,
                 (SELECT COUNT(*) FROM reminder_log rl WHERE rl.unpaid_invoice_id = ui.id) as reminders_sent
               FROM unpaid_invoices ui
               WHERE ui.user_id = ? AND ui.status = 'collected'
               ORDER BY ui.resolved_at DESC LIMIT 10""",
            (user["id"],),
        ).fetchall()

    month_s = dict(month_stats) if month_stats else {
        "total_invoices": 0, "total_collected": 0,
        "total_amount": 0, "total_amount_collected": 0,
    }
    at = dict(all_time)

    data = {
        "request": request,
        "user": user,
        "setup_complete": bool(user.get("setup_complete")),
        "active_overdue": active_count,
        "active_open": open_count,
        "month_collected": month_s["total_collected"],
        "month_amount_collected": month_s["total_amount_collected"] / 100 if month_s["total_amount_collected"] else 0,
        "all_time_collected": at["collected"],
        "all_time_amount": at["amount_collected"] / 100 if at["amount_collected"] else 0,
        "all_time_invoices": at["invoices"],
        "collection_rate": round(at["collected"] / max(at["invoices"], 1) * 100, 1),
        "recent": [dict(r) for r in recent],
        "collected": [dict(c) for c in collected],
    }

    return render(request, "dashboard.html", data)
