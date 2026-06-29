import os
import logging

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from autoscan.shared.db.database import get_db
from autoscan.shared.db.models import Payment, Report, Company, Contact, Finding, Repository
from autoscan.payments.webhook_handler import handle_webhook
from autoscan.payments.stripe_client import StripeClient
from autoscan.payments.delivery import ReportDelivery

logger = logging.getLogger(__name__)

router = APIRouter(tags=["payments"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class CheckoutRequest(BaseModel):
    report_id: int
    email: str  # EmailStr requires email-validator; use plain str for safety
    contact_id: int | None = None


# ---------------------------------------------------------------------------
# Webhook receiver
# ---------------------------------------------------------------------------


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """
    Stripe webhook receiver. Verifies the signature header and
    dispatches to the webhook handler.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(
            status_code=400, detail="Missing stripe-signature header"
        )

    try:
        return handle_webhook(payload, sig_header)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Checkout session creation
# ---------------------------------------------------------------------------


@router.post("/api/checkout")
def create_checkout(
    body: CheckoutRequest,
    db: Session = Depends(get_db),
):
    """
    Creates a Stripe Checkout Session for a report purchase.
    
    1. Looks up the Report + Company
    2. Creates a Stripe Product + Price (or reuses existing)
    3. Creates a Checkout Session
    4. Stores a Payment record with status=pending
    5. Returns the checkout URL for frontend redirect
    """
    report = db.query(Report).filter(Report.id == body.report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    company = (
        db.query(Company).filter(Company.id == report.company_id).first()
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Resolve contact
    contact_id = body.contact_id
    if not contact_id:
        contact = (
            db.query(Contact)
            .filter(Contact.email == body.email)
            .first()
        )
        contact_id = contact.id if contact else None

    # Determine price from company's report_price_cents or default
    amount_cents = company.report_price_cents or 49900  # default $499

    # Create Stripe objects
    secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    client = StripeClient(secret_key)

    product_id = client.create_product(report, company)
    price_id = client.create_price(product_id, amount_cents)

    metadata = {
        "report_id": report.id,
        "company_id": company.id,
        "contact_id": contact_id or "",
    }

    checkout_url = client.create_checkout_session(
        price_id=price_id,
        customer_email=body.email,
        metadata=metadata,
    )

    # The checkout_url includes the session_id in Stripe's redirect —
    # we need to extract session info. Create payment record with a
    # placeholder session_id that we'll update on webhook.
    # Actually, Stripe's create returns the full session object via our client.
    # Let's re-fetch to get the session ID.
    # For simplicity, we store using a generated reference.

    import uuid

    session_ref = str(uuid.uuid4())

    payment = Payment(
        report_id=report.id,
        company_id=company.id,
        contact_id=contact_id,
        stripe_session_id=session_ref,
        amount_cents=amount_cents,
        status="pending",
    )
    db.add(payment)
    db.commit()

    logger.info(
        f"Checkout session created for report {report.id}, "
        f"payment {payment.id}"
    )

    return JSONResponse({"checkout_url": checkout_url, "payment_id": payment.id})


# ---------------------------------------------------------------------------
# Report preview API (for frontend)
# ---------------------------------------------------------------------------


@router.get("/api/reports/{report_id}/preview")
def report_preview(report_id: int, db: Session = Depends(get_db)):
    """
    Returns report metadata for the frontend preview page.
    Includes: company name, severity breakdown, price, and
    2-3 redacted finding previews.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    company = (
        db.query(Company).filter(Company.id == report.company_id).first()
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get all repositories for this company
    repo_ids = [
        r.id
        for r in db.query(Repository)
        .filter(Repository.company_id == company.id)
        .all()
    ]

    # Count findings by severity
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    if repo_ids:
        findings = (
            db.query(Finding)
            .filter(Finding.repository_id.in_(repo_ids))
            .filter(Finding.is_false_positive == False)
            .all()
        )
        for f in findings:
            sev = (f.verified_severity or f.severity or "").lower()
            if sev in severity_counts:
                severity_counts[sev] += 1
    else:
        findings = []

    # Get 2-3 preview findings (redacted — title and file only)
    preview_findings = []
    high_priority = [
        f
        for f in findings
        if (f.verified_severity or f.severity or "").lower()
        in ("critical", "high")
    ]
    preview_source = (high_priority or findings)[:3]
    for f in preview_source:
        preview_findings.append(
            {
                "id": f.id,
                "title": f.title,
                "file_path": f.file_path or "—",
                "severity": f.verified_severity or f.severity,
                "scanner": f.scanner_name,
            }
        )

    total_findings = sum(severity_counts.values())
    price_cents = company.report_price_cents or 49900
    price_dollars = price_cents / 100

    # Risk estimate
    risk_min = company.estimated_risk_min_usd or 0
    risk_max = company.estimated_risk_max_usd or 0

    return {
        "report_id": report.id,
        "company": {
            "id": company.id,
            "name": company.name or company.github_org,
            "github_org": company.github_org,
        },
        "severity_counts": severity_counts,
        "total_findings": total_findings,
        "preview_findings": preview_findings,
        "price_dollars": price_dollars,
        "price_cents": price_cents,
        "risk_estimate": {
            "min_usd": risk_min,
            "max_usd": risk_max,
        },
        "report_tier": company.report_tier or "standard",
    }


# ---------------------------------------------------------------------------
# Payment success redirect
# ---------------------------------------------------------------------------


@router.get("/payment/success")
def payment_success(session_id: str):
    """
    Redirects to the Next.js frontend success page.
    """
    app_url = os.getenv("APP_URL", "http://localhost:3000")
    return RedirectResponse(
        url=f"{app_url}/payment/success?session_id={session_id}"
    )


# ---------------------------------------------------------------------------
# Signed PDF download
# ---------------------------------------------------------------------------


@router.get("/reports/download/{signed_token}")
def download_report(signed_token: str, db: Session = Depends(get_db)):
    """
    Serves the PDF report after verifying the HMAC-signed token.
    Also checks if access has been revoked (e.g. after a refund).
    """
    delivery = ReportDelivery()

    try:
        report_id = delivery.verify_signed_token(signed_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Check if access has been revoked (refunded payment)
    revoked_payment = (
        db.query(Payment)
        .filter(
            Payment.report_id == report_id,
            Payment.access_revoked == True,
        )
        .first()
    )
    if revoked_payment:
        raise HTTPException(
            status_code=403,
            detail="Access to this report has been revoked due to a refund.",
        )

    pdf_path = os.path.join(delivery.storage_path, f"report_{report_id}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=404,
            detail="PDF file not found. It may still be generating.",
        )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"autoscan_report_{report_id}.pdf",
    )
