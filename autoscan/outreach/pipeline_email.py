import argparse
import logging
import os
import uuid

from sqlalchemy.orm import Session
from autoscan.shared.db.database import SessionLocal
from autoscan.shared.db.models import Company, Contact, Email, Repository, Finding
from autoscan.outreach.email_composer import EmailComposer
from autoscan.outreach.sender import EmailSender

logger = logging.getLogger(__name__)

def run_outreach(company_id: int = None, limit: int = 10, dry_run: bool = False):
    db = SessionLocal()
    
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "dummy")
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "dummy")
    from_email = os.getenv("FROM_EMAIL", "security@autoscan.io")

    if not dry_run and (anthropic_api_key == "dummy" or sendgrid_api_key == "dummy"):
        logger.warning("Missing API keys for Anthropic or SendGrid. Aborting outreach.")
        return

    composer = EmailComposer(anthropic_api_key)
    sender = EmailSender(sendgrid_api_key, from_email)

    try:
        query = db.query(Company).filter(Company.status == 'contacts_found')
        if company_id:
            query = query.filter(Company.id == company_id)
        
        companies = query.limit(limit).all()

        for company in companies:
            logger.info(f"Processing company: {company.name} ({company.id})")
            
            # Find best contact
            contact = db.query(Contact).filter(Contact.company_id == company.id).order_by(Contact.score.desc()).first()
            if not contact:
                logger.warning(f"No contacts found for company {company.id}. Skipping.")
                continue

            # Fetch findings for the company
            findings = db.query(Finding).join(Repository).filter(Repository.company_id == company.id).all()
            
            # Price
            price = (company.report_price_cents / 100.0) if company.report_price_cents else 500.00
            
            # Placeholder for T-10 (Stripe Checkout)
            checkout_session_id = f"cs_test_{uuid.uuid4().hex[:8]}"
            report_url = f"https://app.autoscan.io/checkout/{checkout_session_id}"

            # We must create the Email record first to get its ID for the tracking pixel
            new_email = Email(
                company_id=company.id,
                contact_id=contact.id,
                subject="", # placeholder
                html_body="", # placeholder
                text_body="", # placeholder
                checkout_session_id=checkout_session_id
            )
            db.add(new_email)
            db.commit() # Commit to generate new_email.id
            db.refresh(new_email)

            try:
                # Compose the email
                email_data = composer.compose_initial_email(
                    company=company, 
                    contact=contact, 
                    findings=findings, 
                    report_url=report_url, 
                    price=price, 
                    email_id=new_email.id
                )
                
                new_email.subject = email_data["subject"]
                new_email.html_body = email_data["html_body"]
                new_email.text_body = email_data["text_body"]

                if dry_run:
                    logger.info(f"[DRY RUN] Would send to {contact.email}: {email_data['subject']}")
                    # Update company status to outreach_sent for dry run as well just to show state progression
                    company.status = 'outreach_sent'
                    db.commit()
                else:
                    message_id = sender.send(
                        to_email=contact.email,
                        to_name=contact.first_name or "",
                        subject=email_data["subject"],
                        html_body=email_data["html_body"],
                        text_body=email_data["text_body"],
                        email_id=new_email.id
                    )
                    logger.info(f"Email sent with ID: {message_id}")
                    company.status = 'outreach_sent'
                    db.commit()
                    
            except Exception as compose_err:
                logger.error(f"Failed to process email for company {company.id}: {compose_err}")
                db.delete(new_email)
                db.commit()

    except Exception as e:
        logger.error(f"Error in outreach pipeline: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Run the AutoScan Outreach Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Run without actually sending emails")
    parser.add_argument("--company-id", type=int, help="Specific company ID to target")
    parser.add_argument("--limit", type=int, default=10, help="Max companies to process")
    
    args = parser.parse_args()
    
    run_outreach(company_id=args.company_id, limit=args.limit, dry_run=args.dry_run)
