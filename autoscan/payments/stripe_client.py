import os
import stripe
import logging

from autoscan.shared.db.models import Report, Company

logger = logging.getLogger(__name__)


class StripeClient:
    """
    Handles all Stripe API interactions: product creation, pricing,
    checkout sessions, and session retrieval.
    """

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        stripe.api_key = self.secret_key

    def create_product(self, report: Report, company: Company) -> str:
        """
        Create a Stripe Product for the given report and company.
        Returns the Stripe product ID.
        """
        try:
            product = stripe.Product.create(
                name=f"Security Analysis Report - {company.name or company.github_org}",
                description=(
                    f"Full detailed vulnerability analysis report for "
                    f"{company.name or company.github_org}. Includes AI-verified "
                    f"findings, reproduction steps, and remediation guidance."
                ),
                metadata={
                    "report_id": str(report.id),
                    "company_id": str(company.id),
                    "source": "autoscan",
                },
            )
            logger.info(
                f"Created Stripe product {product.id} for report {report.id}"
            )
            return product.id
        except stripe.StripeError as e:
            logger.error(f"Stripe API error creating product: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating Stripe product: {e}")
            raise

    def create_price(self, product_id: str, amount_cents: int) -> str:
        """
        Create a one-time Stripe Price for the given product.
        Returns the Stripe price ID.
        """
        try:
            price = stripe.Price.create(
                product=product_id,
                unit_amount=amount_cents,
                currency="usd",
            )
            logger.info(
                f"Created Stripe price {price.id} — ${amount_cents / 100:.2f}"
            )
            return price.id
        except stripe.StripeError as e:
            logger.error(f"Stripe API error creating price: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating Stripe price: {e}")
            raise

    def create_checkout_session(
        self,
        price_id: str,
        customer_email: str,
        metadata: dict,
    ) -> str:
        """
        Create a Stripe Checkout Session.
        
        metadata must contain: report_id, company_id, contact_id
        
        Returns the checkout session URL for redirect.
        """
        app_url = os.getenv("APP_URL", "http://localhost:3000")
        report_id = metadata.get("report_id", "")

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    },
                ],
                mode="payment",
                customer_email=customer_email,
                success_url=f"{app_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{app_url}/report/{report_id}",
                metadata={
                    "report_id": str(metadata.get("report_id", "")),
                    "company_id": str(metadata.get("company_id", "")),
                    "contact_id": str(metadata.get("contact_id", "")),
                },
            )
            logger.info(
                f"Created checkout session {session.id} for report {report_id}"
            )
            return session.url
        except stripe.StripeError as e:
            logger.error(f"Stripe API error creating checkout session: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating checkout session: {e}")
            raise

    def retrieve_session(self, session_id: str) -> dict:
        """
        Retrieve a Stripe Checkout Session by ID.
        Returns the full session object as a dict.
        """
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return session
        except stripe.StripeError as e:
            logger.error(f"Stripe API error retrieving session {session_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving session {session_id}: {e}")
            raise
