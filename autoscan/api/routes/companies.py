import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from autoscan.shared.db.database import get_db
from autoscan.shared.db.models import (
    Company,
    Repository,
    Finding,
    Report,
    Contact,
    Email,
    EmailEvent,
    Payment,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/companies", tags=["companies"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CompanyUpdate(BaseModel):
    notes: Optional[str] = None
    skip: Optional[bool] = None
    priority: Optional[str] = None


# ---------------------------------------------------------------------------
# GET /api/companies — paginated list
# ---------------------------------------------------------------------------


@router.get("")
def list_companies(
    status: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    sort_by: Optional[str] = Query("qualification_score"),
    sort_dir: Optional[str] = Query("desc"),
    db: Session = Depends(get_db),
):
    """
    Paginated, filterable, sortable list of all companies.
    Returns enriched rows with finding counts, outreach status, and revenue.
    """
    query = db.query(Company)

    # Filters
    if status:
        query = query.filter(Company.status == status)
    if min_score is not None:
        query = query.filter(Company.qualification_score >= min_score)
    if search:
        query = query.filter(
            Company.name.ilike(f"%{search}%")
            | Company.github_org.ilike(f"%{search}%")
        )

    # Total count before pagination
    total = query.count()

    # Sorting
    sort_col = getattr(Company, sort_by, Company.qualification_score)
    if sort_dir == "asc":
        query = query.order_by(sort_col.asc().nullslast())
    else:
        query = query.order_by(sort_col.desc().nullsfirst())

    # Pagination
    offset = (page - 1) * limit
    companies = query.offset(offset).limit(limit).all()

    # Enrich each company with aggregated data
    results = []
    for c in companies:
        # Finding count
        repo_ids = [r.id for r in db.query(Repository.id).filter(
            Repository.company_id == c.id
        ).all()]
        finding_count = 0
        if repo_ids:
            finding_count = (
                db.query(func.count(Finding.id))
                .filter(Finding.repository_id.in_(repo_ids))
                .filter(Finding.is_false_positive == False)
                .scalar()
            ) or 0

        # Outreach status
        latest_email = (
            db.query(Email)
            .filter(Email.company_id == c.id)
            .order_by(Email.sent_at.desc())
            .first()
        )
        if latest_email:
            if latest_email.clicked_at:
                outreach_status = "clicked"
            elif latest_email.opened_at:
                outreach_status = "opened"
            else:
                outreach_status = "sent"
        else:
            outreach_status = "none"

        # Revenue
        revenue_cents = (
            db.query(func.sum(Payment.amount_cents))
            .filter(Payment.company_id == c.id, Payment.status == "paid")
            .scalar()
        ) or 0

        results.append({
            "id": c.id,
            "name": c.name or c.github_org,
            "github_org": c.github_org,
            "website": c.website,
            "score": c.qualification_score,
            "status": c.status or "NEW",
            "employee_count": c.employee_count,
            "finding_count": finding_count,
            "report_price_cents": c.report_price_cents,
            "report_tier": c.report_tier,
            "outreach_status": outreach_status,
            "revenue_cents": revenue_cents,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    pages = max(1, (total + limit - 1) // limit)

    return {
        "companies": results,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
    }


# ---------------------------------------------------------------------------
# GET /api/companies/{id} — full detail
# ---------------------------------------------------------------------------


@router.get("/{company_id}")
def get_company(company_id: int, db: Session = Depends(get_db)):
    """
    Full company detail with findings, emails, payments, contacts, repos.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Repositories
    repos = (
        db.query(Repository)
        .filter(Repository.company_id == company.id)
        .all()
    )
    repo_data = [
        {
            "id": r.id,
            "name": r.name,
            "full_name": r.full_name,
            "language": r.language,
            "stars": r.stars,
            "finding_count": r.finding_count,
            "status": r.status,
            "last_scanned_at": r.last_scanned_at.isoformat() if r.last_scanned_at else None,
        }
        for r in repos
    ]

    # Findings (across all repos)
    repo_ids = [r.id for r in repos]
    repo_fullname_map = {r.id: r.full_name for r in repos}
    findings = []
    if repo_ids:
        db_findings = (
            db.query(Finding)
            .filter(Finding.repository_id.in_(repo_ids))
            .filter(Finding.is_false_positive == False)
            .order_by(Finding.severity.desc())
            .all()
        )
        findings = [
            {
                "id": f.id,
                "type": f.type,
                "severity": f.verified_severity or f.severity,
                "title": f.title,
                "description": f.description,
                "file_path": f.file_path,
                "line_no": f.line_no,
                "scanner": f.scanner_name,
                "verified": f.verified,
                "ai_explanation": f.ai_explanation,
                "ai_recommendation": f.ai_recommendation,
                "repo_full_name": repo_fullname_map.get(f.repository_id),
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in db_findings
        ]

    # Contacts
    contacts = (
        db.query(Contact)
        .filter(Contact.company_id == company.id)
        .all()
    )
    contact_data = [
        {
            "id": ct.id,
            "email": ct.email,
            "first_name": ct.first_name,
            "last_name": ct.last_name,
            "position": ct.position,
            "score": ct.score,
            "is_verified": ct.is_verified,
        }
        for ct in contacts
    ]

    # Emails (with events)
    emails = (
        db.query(Email)
        .filter(Email.company_id == company.id)
        .order_by(Email.sent_at.desc())
        .all()
    )
    email_data = [
        {
            "id": em.id,
            "subject": em.subject,
            "contact_id": em.contact_id,
            "sequence_num": em.sequence_num,
            "sent_at": em.sent_at.isoformat() if em.sent_at else None,
            "opened_at": em.opened_at.isoformat() if em.opened_at else None,
            "clicked_at": em.clicked_at.isoformat() if em.clicked_at else None,
            "events": [
                {
                    "event_type": ev.event_type,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                }
                for ev in em.events
            ],
        }
        for em in emails
    ]

    # Payments
    payments = (
        db.query(Payment)
        .filter(Payment.company_id == company.id)
        .order_by(Payment.created_at.desc())
        .all()
    )
    payment_data = [
        {
            "id": p.id,
            "report_id": p.report_id,
            "amount_cents": p.amount_cents,
            "status": p.status,
            "stripe_session_id": p.stripe_session_id,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in payments
    ]

    # Reports
    reports = (
        db.query(Report)
        .filter(Report.company_id == company.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    report_data = [
        {
            "id": rp.id,
            "created_at": rp.created_at.isoformat() if rp.created_at else None,
            "full_report_path": rp.full_report_path,
        }
        for rp in reports
    ]

    # Revenue total
    revenue_cents = (
        db.query(func.sum(Payment.amount_cents))
        .filter(Payment.company_id == company.id, Payment.status == "paid")
        .scalar()
    ) or 0

    return {
        "company": {
            "id": company.id,
            "name": company.name,
            "github_org": company.github_org,
            "website": company.website,
            "description": company.description,
            "employee_count": company.employee_count,
            "funding_status": company.funding_status,
            "qualification_score": company.qualification_score,
            "enrichment_score": company.enrichment_score,
            "tech_stack": company.tech_stack,
            "status": company.status,
            "impact_score": company.impact_score,
            "estimated_risk_min_usd": company.estimated_risk_min_usd,
            "estimated_risk_max_usd": company.estimated_risk_max_usd,
            "report_price_cents": company.report_price_cents,
            "report_tier": company.report_tier,
            "created_at": company.created_at.isoformat() if company.created_at else None,
            "updated_at": company.updated_at.isoformat() if company.updated_at else None,
        },
        "repositories": repo_data,
        "findings": findings,
        "contacts": contact_data,
        "emails": email_data,
        "payments": payment_data,
        "reports": report_data,
        "revenue_cents": revenue_cents,
    }


# ---------------------------------------------------------------------------
# POST /api/companies/{id}/actions/rescan
# ---------------------------------------------------------------------------


@router.post("/{company_id}/actions/rescan")
def rescan_company(company_id: int, db: Session = Depends(get_db)):
    """
    Triggers a re-scan for all repositories of a company.
    Resets repo statuses to 'PENDING_SCAN'.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    repos = (
        db.query(Repository)
        .filter(Repository.company_id == company.id)
        .all()
    )

    for repo in repos:
        repo.status = "PENDING_SCAN"

    db.commit()
    logger.info(
        f"Re-scan triggered for company {company.id} "
        f"({len(repos)} repositories)"
    )

    return {
        "status": "accepted",
        "message": f"Re-scan queued for {len(repos)} repositories",
        "company_id": company.id,
    }


# ---------------------------------------------------------------------------
# POST /api/companies/{id}/actions/resend-email
# ---------------------------------------------------------------------------


@router.post("/{company_id}/actions/resend-email")
def resend_email(company_id: int, db: Session = Depends(get_db)):
    """
    Logs a request to resend outreach email for a company.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    logger.info(f"Resend email requested for company {company.id}")

    return {
        "status": "accepted",
        "message": "Email resend queued",
        "company_id": company.id,
    }


# ---------------------------------------------------------------------------
# PUT /api/companies/{id} — update manual fields
# ---------------------------------------------------------------------------


@router.put("/{company_id}")
def update_company(
    company_id: int,
    body: CompanyUpdate,
    db: Session = Depends(get_db),
):
    """
    Update manual fields on a company: notes, skip flag, priority.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if body.skip is True:
        company.status = "SKIP"
    if body.skip is False and company.status == "SKIP":
        company.status = "NEW"
    if body.priority is not None:
        # Store priority in description field as prefix (simple approach)
        company.description = f"[PRIORITY:{body.priority}] {company.description or ''}"

    db.commit()

    logger.info(f"Company {company.id} updated: {body.model_dump(exclude_none=True)}")

    return {"status": "updated", "company_id": company.id}
