import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Header, CustomArg

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self, sendgrid_api_key: str, from_email: str):
        self.sg = SendGridAPIClient(sendgrid_api_key)
        self.from_email = from_email

    def send(self, to_email: str, to_name: str, subject: str, html_body: str, text_body: str, email_id: int = None) -> str:
        message = Mail(
            from_email=Email(self.from_email),
            to_emails=To(to_email, to_name),
            subject=subject,
            html_content=Content("text/html", html_body),
            plain_text_content=Content("text/plain", text_body)
        )
        
        # Add basic List-Unsubscribe header
        domain = self.from_email.split('@')[-1] if '@' in self.from_email else 'example.com'
        message.add_header(Header("List-Unsubscribe", f"<mailto:unsubscribe@{domain}>"))
        
        if email_id is not None:
            message.add_custom_arg(CustomArg("email_id", str(email_id)))

        try:
            response = self.sg.send(message)
            # Extract message ID from headers if present
            message_id = response.headers.get('X-Message-Id', 'unknown_id')
            if isinstance(message_id, list) and len(message_id) > 0:
                message_id = message_id[0]
            logger.info(f"Email sent successfully. internal_email_id: {email_id}, to: {to_email}, message_id: {message_id}")
            return str(message_id)
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            raise
