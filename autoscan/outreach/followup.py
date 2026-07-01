import os
import logging
from datetime import datetime, timedelta, timezone

from autoscan.shared.db.database import SessionLocal
from autoscan.shared.db.models import Email
from autoscan.outreach.email_composer import EmailComposer
from autoscan.outreach.sender import EmailSender

logger = logging.getLogger(__name__)

def check_and_send_followups(dry_run: bool = False):
    gemini_api_key = os.getenv("GEMINI_API_KEY", "dummy")
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "dummy")
    from_email = os.getenv("FROM_EMAIL", "security@autoscan.io")
    
    if not dry_run and (gemini_api_key == "dummy" or sendgrid_api_key == "dummy"):
        logger.warning("Missing real API keys. Aborting followups.")
        return

    composer = EmailComposer(gemini_api_key)
    sender = EmailSender(sendgrid_api_key, from_email)

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        five_days_ago = now - timedelta(days=5)

        # 1. No open > 5 days -> send sequence 2
        unopened_emails = db.query(Email).filter(
            Email.sequence_num == 1,
            Email.opened_at.is_(None),
            Email.sent_at <= five_days_ago
        ).all()

        for email in unopened_emails:
            logger.info(f"Sending Followup 2 for Email ID: {email.id}")
            if not dry_run:
                email_data = composer.compose_followup_email(email.company, email.contact, 2, email.id)
                sender.send(
                    to_email=email.contact.email,
                    to_name=email.contact.first_name or "",
                    subject=email_data["subject"],
                    html_body=email_data["html_body"],
                    text_body=email_data["text_body"],
                    email_id=email.id
                )
                email.sequence_num = 2
                email.sent_at = now
                db.commit()
            
        # 2. Opened but no click > 5 days -> send sequence 3
        # Assuming sequence_num could be 1 or 2. If opened but not clicked, we jump to 3.
        unclicked_opened_emails = db.query(Email).filter(
            Email.sequence_num < 3,
            Email.opened_at.isnot(None),
            Email.clicked_at.is_(None),
            Email.opened_at <= five_days_ago
        ).all()

        for email in unclicked_opened_emails:
            logger.info(f"Sending Followup 3 for Email ID: {email.id}")
            if not dry_run:
                email_data = composer.compose_followup_email(email.company, email.contact, 3, email.id)
                sender.send(
                    to_email=email.contact.email,
                    to_name=email.contact.first_name or "",
                    subject=email_data["subject"],
                    html_body=email_data["html_body"],
                    text_body=email_data["text_body"],
                    email_id=email.id
                )
                email.sequence_num = 3
                email.sent_at = now
                db.commit()

    except Exception as e:
        logger.error(f"Error processing followups: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    check_and_send_followups(dry_run=True)
