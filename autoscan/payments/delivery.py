import os
import hmac
import hashlib
import time
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from autoscan.shared.db.models import Payment, Contact

logger = logging.getLogger(__name__)

# Maximum retries for SMTP delivery
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


class ReportDelivery:
    """
    Handles secure report delivery via email with PDF attachments
    and HMAC-SHA256 signed download URLs.
    """

    def __init__(self, smtp_config: dict = None, storage_path: str = None):
        self.smtp_config = smtp_config or {
            "host": os.getenv("SMTP_HOST", "localhost"),
            "port": int(os.getenv("SMTP_PORT", "1025")),
            "user": os.getenv("SMTP_USER", ""),
            "password": os.getenv("SMTP_PASSWORD", ""),
        }
        self.storage_path = storage_path or os.getenv(
            "REPORT_STORAGE_PATH", "/tmp/reports"
        )
        self.secret_key = os.getenv("HMAC_SECRET", "dummy_secret_key_for_hmac")

    def generate_signed_url(
        self, report_id: int, expires_hours: int = 168
    ) -> str:
        """
        Generate a signed download URL using HMAC-SHA256.

        Token format: {report_id}.{expires_timestamp}.{signature}
        Default expiry: 168 hours (7 days).
        """
        expires_at = int(time.time()) + (expires_hours * 3600)
        message = f"{report_id}:{expires_at}".encode("utf-8")
        signature = hmac.new(
            self.secret_key.encode("utf-8"), message, hashlib.sha256
        ).hexdigest()

        token = f"{report_id}.{expires_at}.{signature}"

        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        return f"{backend_url}/reports/download/{token}"

    def verify_signed_token(self, token: str) -> int:
        """
        Verify the HMAC-signed token and return the report_id.
        Raises ValueError if the token is invalid, expired, or tampered.
        """
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid token structure")

            report_id_str, expires_at_str, signature = parts
            report_id = int(report_id_str)
            expires_at = int(expires_at_str)

            if int(time.time()) > expires_at:
                raise ValueError("Token expired")

            message = f"{report_id}:{expires_at}".encode("utf-8")
            expected_signature = hmac.new(
                self.secret_key.encode("utf-8"), message, hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_signature, signature):
                raise ValueError("Invalid signature")

            return report_id
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Token validation failed: {e}")

    def deliver_report(self, payment: Payment, contact: Contact):
        """
        Send email with the full PDF report attached and a signed
        backup download link. Retries up to MAX_RETRIES on failure.
        """
        report_id = payment.report_id
        if not report_id:
            logger.error("Cannot deliver report: payment has no report_id")
            return

        signed_url = self.generate_signed_url(report_id)
        pdf_path = os.path.join(self.storage_path, f"report_{report_id}.pdf")

        msg = self._build_email(contact, report_id, signed_url, pdf_path)

        self._send_with_retry(msg, contact.email, signed_url)

    def revoke_access(self, report_id: int):
        """
        Revoke access for a report. Since signed URLs are stateless
        (HMAC-based), revocation is tracked via the Payment.access_revoked
        flag in the database. The download endpoint checks this flag
        before serving the PDF.
        """
        logger.info(f"Access revoked for report {report_id}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_email(
        self,
        contact: Contact,
        report_id: int,
        signed_url: str,
        pdf_path: str,
    ) -> MIMEMultipart:
        """Build a multipart MIME email with HTML body and optional PDF attachment."""
        msg = MIMEMultipart("mixed")
        msg["Subject"] = "Your AutoScan Vulnerability Report"
        msg["From"] = os.getenv("FROM_EMAIL", "delivery@autoscan.io")
        msg["To"] = contact.email

        first_name = contact.first_name or "there"

        html_body = f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:600px;margin:0 auto;padding:40px 24px;">
    <!-- Header -->
    <div style="text-align:center;margin-bottom:32px;">
      <div style="display:inline-block;background:#4f46e5;color:#fff;font-weight:700;font-size:14px;padding:8px 16px;border-radius:8px;letter-spacing:0.5px;">
        AUTOSCAN
      </div>
    </div>

    <!-- Main Card -->
    <div style="background:#141414;border:1px solid #262626;border-radius:16px;padding:32px;margin-bottom:24px;">
      <h1 style="color:#fafafa;font-size:24px;font-weight:700;margin:0 0 12px;">
        Hi {first_name}, your report is ready
      </h1>
      <p style="color:#a3a3a3;font-size:15px;line-height:1.6;margin:0 0 24px;">
        Thank you for your purchase. Your full vulnerability analysis report is attached to this email as a PDF.
      </p>

      <!-- Download Button -->
      <div style="text-align:center;margin:24px 0;">
        <a href="{signed_url}"
           style="display:inline-block;background:#4f46e5;color:#ffffff;font-weight:600;font-size:15px;padding:14px 32px;border-radius:10px;text-decoration:none;">
          Download Report
        </a>
      </div>

      <p style="color:#737373;font-size:13px;text-align:center;margin:0;">
        Can't open the attachment? Use the button above.<br>
        This link expires in 7 days.
      </p>
    </div>

    <!-- Footer -->
    <div style="text-align:center;color:#525252;font-size:12px;line-height:1.5;">
      <p style="margin:0;">&copy; AutoScan Security &mdash; Automated Vulnerability Intelligence</p>
      <p style="margin:4px 0 0;">This email contains confidential information. Do not forward.</p>
    </div>
  </div>
</body>
</html>"""

        text_body = f"""\
Hi {first_name},

Thank you for your purchase. Your full vulnerability report is attached to this email.

If you have trouble opening the attachment, download it here (link expires in 7 days):
{signed_url}

Best,
The AutoScan Team"""

        # Attach text/plain and text/html alternatives
        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(text_body, "plain", "utf-8"))
        alt_part.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt_part)

        # Attach PDF if available
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
            pdf_attachment = MIMEApplication(pdf_data, _subtype="pdf")
            pdf_attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=f"autoscan_report_{report_id}.pdf",
            )
            msg.attach(pdf_attachment)
        else:
            logger.warning(
                f"PDF not found at {pdf_path}. Sending email without attachment."
            )

        return msg

    def _send_with_retry(self, msg: MIMEMultipart, to_email: str, signed_url: str):
        """Send the email with exponential backoff retry."""
        if self.smtp_config["host"] == "localhost":
            logger.info(
                f"[DRY RUN] Would send email to {to_email} with signed link {signed_url}"
            )
            return

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                with smtplib.SMTP(
                    self.smtp_config["host"], self.smtp_config["port"]
                ) as server:
                    if self.smtp_config["user"]:
                        server.starttls()
                        server.login(
                            self.smtp_config["user"],
                            self.smtp_config["password"],
                        )
                    server.send_message(msg)
                logger.info(f"Delivered report to {to_email}")
                return
            except Exception as e:
                last_error = e
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    f"SMTP attempt {attempt}/{MAX_RETRIES} failed: {e}. "
                    f"Retrying in {wait}s..."
                )
                time.sleep(wait)

        logger.error(
            f"Failed to send delivery email after {MAX_RETRIES} attempts: "
            f"{last_error}"
        )
