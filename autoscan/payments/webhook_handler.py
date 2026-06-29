import os
import stripe
import logging

from sqlalchemy.orm import Session
from autoscan.shared.db.database import SessionLocal
from autoscan.shared.db.models import Payment, Contact
from autoscan.payments.delivery import ReportDelivery

logger = logging.getLogger(__name__)


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Main webhook entry point. Verifies the Stripe signature,
    dispatches to the appropriate handler, and returns a status dict.

    Each handler is idempotent — it checks whether the event
    has already been processed before making any state changes.
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        logger.error("Invalid webhook payload")
        raise
    except stripe.SignatureVerificationError:
        logger.error("Invalid webhook signature")
        raise

    event_type = event["type"]
    logger.info(f"Received Stripe webhook: {event_type}")

    db = SessionLocal()
    try:
        if event_type == "checkout.session.completed":
            session_data = event["data"]["object"]
            _handle_checkout_session_completed(session_data, db)

        elif event_type == "payment_intent.payment_failed":
            intent = event["data"]["object"]
            _handle_payment_failed(intent, db)

        elif event_type == "charge.refunded":
            charge = event["data"]["object"]
            _handle_charge_refunded(charge, db)

        else:
            logger.info(f"Unhandled event type: {event_type}")

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error handling webhook event {event_type}: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Individual event handlers (all idempotent)
# ---------------------------------------------------------------------------


def _handle_checkout_session_completed(session: dict, db: Session):
    """
    Marks the payment as paid and triggers report delivery.
    Idempotent: skips if payment is already marked as paid.
    """
    session_id = session.get("id")
    payment_intent_id = session.get("payment_intent")

    payment = (
        db.query(Payment)
        .filter(Payment.stripe_session_id == session_id)
        .first()
    )

    if not payment:
        # The Payment record is created when we generate the checkout session.
        # If it's missing, the webhook arrived before the DB write — log and skip.
        logger.warning(
            f"Payment with session_id {session_id} not found in DB."
        )
        return

    # Idempotency check
    if payment.status == "paid":
        logger.info(
            f"Payment {payment.id} already marked as paid. Skipping."
        )
        return

    payment.status = "paid"
    if payment_intent_id:
        payment.stripe_payment_intent_id = payment_intent_id
    db.commit()
    logger.info(f"Payment {payment.id} marked as paid.")

    # Trigger report delivery
    contact = (
        db.query(Contact).filter(Contact.id == payment.contact_id).first()
    )
    if contact:
        delivery = ReportDelivery()
        try:
            delivery.deliver_report(payment, contact)
        except Exception as e:
            logger.error(
                f"Failed to deliver report for payment {payment.id}: {e}"
            )


def _handle_payment_failed(intent: dict, db: Session):
    """
    Updates the payment status to 'failed' when a PaymentIntent fails.
    Idempotent: skips if payment is already marked as failed.
    """
    payment_intent_id = intent.get("id")

    # Try to find the payment by stripe_payment_intent_id first
    payment = (
        db.query(Payment)
        .filter(Payment.stripe_payment_intent_id == payment_intent_id)
        .first()
    )

    # If not found by PI ID, try to find by metadata
    if not payment:
        metadata = intent.get("metadata", {})
        report_id = metadata.get("report_id")
        if report_id:
            payment = (
                db.query(Payment)
                .filter(
                    Payment.report_id == int(report_id),
                    Payment.status == "pending",
                )
                .first()
            )

    if not payment:
        logger.warning(
            f"No matching payment found for failed intent {payment_intent_id}"
        )
        return

    # Idempotency check
    if payment.status == "failed":
        logger.info(
            f"Payment {payment.id} already marked as failed. Skipping."
        )
        return

    payment.status = "failed"
    payment.stripe_payment_intent_id = payment_intent_id
    db.commit()
    logger.warning(
        f"Payment {payment.id} marked as failed (intent: {payment_intent_id})"
    )


def _handle_charge_refunded(charge: dict, db: Session):
    """
    Updates the payment status to 'refunded' and revokes report access.
    Idempotent: skips if payment is already marked as refunded.
    """
    payment_intent_id = charge.get("payment_intent")

    payment = (
        db.query(Payment)
        .filter(Payment.stripe_payment_intent_id == payment_intent_id)
        .first()
    )

    if not payment:
        logger.warning(
            f"No matching payment found for refunded charge "
            f"(PI: {payment_intent_id})"
        )
        return

    # Idempotency check
    if payment.status == "refunded":
        logger.info(
            f"Payment {payment.id} already marked as refunded. Skipping."
        )
        return

    payment.status = "refunded"
    payment.access_revoked = True
    db.commit()
    logger.info(
        f"Payment {payment.id} marked as refunded. Access revoked."
    )
