import logging
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from autoscan.shared.db.database import get_db
from autoscan.shared.db.models import (
    Company,
    Repository,
    Finding,
    Report,
    Contact,
    Email,
    Payment,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------------
# GET /api/dashboard/overview
# ---------------------------------------------------------------------------


@router.get("/overview")
def dashboard_overview(db: Session = Depends(get_db)):
    """
    Returns high-level KPIs for the dashboard:
    - companies_by_status: count of companies grouped by status
    - revenue_total_cents: sum of all paid payments
    - paid_count: number of paid payments
    - conversion_rate: paid / total emails sent (or 0)
    - avg_report_price: average report_price_cents across companies
    - top_finding_types: top 10 finding types by frequency
    - costs_total_cents: placeholder COGS
    """

    # --- Companies by status ---
    status_rows = (
        db.query(Company.status, func.count(Company.id))
        .group_by(Company.status)
        .all()
    )
    companies_by_status = {
        (status or "UNKNOWN"): count for status, count in status_rows
    }

    # --- Revenue ---
    revenue_row = (
        db.query(func.sum(Payment.amount_cents))
        .filter(Payment.status == "paid")
        .scalar()
    )
    revenue_total_cents = revenue_row or 0

    paid_count = (
        db.query(func.count(Payment.id))
        .filter(Payment.status == "paid")
        .scalar()
    ) or 0

    # --- Conversion rate (paid / emails sent) ---
    emails_sent = db.query(func.count(Email.id)).scalar() or 0
    conversion_rate = round(paid_count / emails_sent, 4) if emails_sent > 0 else 0.0

    # --- Average report price ---
    avg_price = (
        db.query(func.avg(Company.report_price_cents))
        .filter(Company.report_price_cents.isnot(None))
        .scalar()
    )
    avg_report_price = int(avg_price) if avg_price else 0

    # --- Top finding types ---
    type_rows = (
        db.query(Finding.type, func.count(Finding.id))
        .filter(Finding.is_false_positive == False)
        .group_by(Finding.type)
        .order_by(func.count(Finding.id).desc())
        .limit(10)
        .all()
    )
    top_finding_types = [
        {"type": ftype, "count": fcount} for ftype, fcount in type_rows
    ]

    # --- Costs (placeholder — would come from a costs table) ---
    costs_total_cents = 0

    # --- Recent activity (last 10 events across payments + emails) ---
    recent_payments = (
        db.query(Payment)
        .filter(Payment.status == "paid")
        .order_by(Payment.updated_at.desc())
        .limit(10)
        .all()
    )
    recent_emails = (
        db.query(Email)
        .order_by(Email.sent_at.desc())
        .limit(10)
        .all()
    )

    activity = []
    for p in recent_payments:
        activity.append({
            "type": "payment",
            "description": f"Payment received — ${p.amount_cents / 100:.0f}",
            "company_id": p.company_id,
            "timestamp": p.updated_at.isoformat() if p.updated_at else None,
        })
    for e in recent_emails:
        status = "opened" if e.opened_at else "sent"
        if e.clicked_at:
            status = "clicked"
        activity.append({
            "type": "email",
            "description": f"Email {status}: {e.subject[:50]}",
            "company_id": e.company_id,
            "timestamp": (e.clicked_at or e.opened_at or e.sent_at).isoformat()
            if (e.clicked_at or e.opened_at or e.sent_at)
            else None,
        })

    # Sort by timestamp descending and take top 10
    activity.sort(
        key=lambda x: x.get("timestamp") or "", reverse=True
    )
    recent_activity = activity[:10]

    return {
        "companies_by_status": companies_by_status,
        "revenue_total_cents": revenue_total_cents,
        "paid_count": paid_count,
        "conversion_rate": conversion_rate,
        "avg_report_price": avg_report_price,
        "top_finding_types": top_finding_types,
        "costs_total_cents": costs_total_cents,
        "recent_activity": recent_activity,
    }


# ---------------------------------------------------------------------------
# GET /api/dashboard/funnel
# ---------------------------------------------------------------------------


@router.get("/funnel")
def dashboard_funnel(db: Session = Depends(get_db)):
    """
    Returns counts at each pipeline stage:
    discovered -> qualified -> scanned -> verified -> reported ->
    contacted -> opened -> clicked -> paid
    """

    # discovered: all companies
    discovered = db.query(func.count(Company.id)).scalar() or 0

    # qualified: companies with qualification_score > 0
    qualified = (
        db.query(func.count(Company.id))
        .filter(Company.qualification_score > 0)
        .scalar()
    ) or 0

    # scanned: distinct companies that have repos with last_scanned_at
    scanned = (
        db.query(func.count(distinct(Repository.company_id)))
        .filter(Repository.last_scanned_at.isnot(None))
        .scalar()
    ) or 0

    # verified: distinct companies with verified findings
    verified = (
        db.query(func.count(distinct(Repository.company_id)))
        .join(Finding, Finding.repository_id == Repository.id)
        .filter(Finding.verified == True)
        .scalar()
    ) or 0

    # reported: distinct companies with reports
    reported = (
        db.query(func.count(distinct(Report.company_id))).scalar()
    ) or 0

    # contacted: distinct companies with emails sent
    contacted = (
        db.query(func.count(distinct(Email.company_id))).scalar()
    ) or 0

    # opened: distinct companies with at least one opened email
    opened = (
        db.query(func.count(distinct(Email.company_id)))
        .filter(Email.opened_at.isnot(None))
        .scalar()
    ) or 0

    # clicked: distinct companies with at least one clicked email
    clicked = (
        db.query(func.count(distinct(Email.company_id)))
        .filter(Email.clicked_at.isnot(None))
        .scalar()
    ) or 0

    # paid: distinct companies with paid payments
    paid = (
        db.query(func.count(distinct(Payment.company_id)))
        .filter(Payment.status == "paid")
        .scalar()
    ) or 0

    return {
        "funnel": [
            {"stage": "Discovered", "count": discovered},
            {"stage": "Qualified", "count": qualified},
            {"stage": "Scanned", "count": scanned},
            {"stage": "Verified", "count": verified},
            {"stage": "Reported", "count": reported},
            {"stage": "Contacted", "count": contacted},
            {"stage": "Opened", "count": opened},
            {"stage": "Clicked", "count": clicked},
            {"stage": "Paid", "count": paid},
        ]
    }
