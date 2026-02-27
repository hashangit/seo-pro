"""
Email Service

Handles sending emails via SendGrid.
"""

import logging

from api.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """SendGrid email service for transactional emails."""

    def __init__(self):
        self.settings = get_settings()
        self._client = None

    @property
    def client(self):
        """Lazy-load SendGrid client."""
        if self._client is None:
            try:
                import sendgrid
                self._client = sendgrid.SendGridAPIClient(
                    api_key=self.settings.SENDGRID_API_KEY
                )
            except ImportError:
                logger.warning("sendgrid package not installed. Emails will be logged only.")
                self._client = False
        return self._client if self._client else None

    def _build_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None
    ) -> dict:
        """Build email payload for SendGrid API."""
        return {
            "personalizations": [
                {
                    "to": [{"email": to_email}],
                    "subject": subject,
                }
            ],
            "from": {
                "email": self.settings.SENDGRID_FROM_EMAIL,
                "name": self.settings.SENDGRID_FROM_NAME,
            },
            "content": [
                {
                    "type": "text/plain",
                    "value": text_content or self._html_to_text(html_content),
                },
                {
                    "type": "text/html",
                    "value": html_content,
                },
            ],
        }

    def _html_to_text(self, html: str) -> str:
        """Simple HTML to text conversion."""
        import re
        text = re.sub(r'<br\s*/?>', '\n', html)
        text = re.sub(r'</p>', '\n\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None
    ) -> bool:
        """
        Send an email via SendGrid.

        Returns True if sent successfully, False otherwise.
        In development without API key, logs the email instead.
        """
        if not self.settings.SENDGRID_API_KEY:
            logger.info(
                "email_skipped_no_api_key",
                extra={
                    "to": to_email,
                    "subject": subject,
                }
            )
            # In development, just log the email
            logger.info(f"EMAIL to {to_email}: {subject}")
            return True

        if not self.client:
            logger.warning("email_client_not_available")
            return False

        try:
            payload = self._build_email(to_email, subject, html_content, text_content)
            response = self.client.client.mail.send.post(request_body=payload)

            if response.status_code in (200, 201, 202):
                logger.info(
                    "email_sent",
                    extra={"to": to_email, "subject": subject}
                )
                return True
            else:
                logger.error(
                    "email_send_failed",
                    extra={
                        "to": to_email,
                        "status_code": response.status_code,
                        "response": response.body
                    }
                )
                return False

        except Exception as e:
            logger.error(
                "email_exception",
                extra={"to": to_email, "error": str(e)}
            )
            return False

    def send_credit_request_confirmation(
        self,
        user_email: str,
        invoice_number: str,
        credits: int,
        amount: float,
        currency: str = "USD"
    ) -> bool:
        """Send confirmation email when user requests credits."""
        subject = f"Credit Request Received - {invoice_number}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4F46E5; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .invoice-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .detail {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
                .steps {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .step {{ padding: 10px 0; }}
                .step-number {{ display: inline-block; width: 24px; height: 24px; background: #4F46E5; color: white; border-radius: 50%; text-align: center; line-height: 24px; margin-right: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>SEO Pro</h1>
                    <p>Credit Request Confirmation</p>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>Thank you for your credit request. Here are your invoice details:</p>

                    <div class="invoice-box">
                        <h2>Invoice: {invoice_number}</h2>
                        <div class="detail">
                            <span>Credits:</span>
                            <strong>{credits}</strong>
                        </div>
                        <div class="detail">
                            <span>Amount:</span>
                            <strong>${amount:.2f} {currency}</strong>
                        </div>
                        <div class="detail">
                            <span>Status:</span>
                            <strong>Pending Payment</strong>
                        </div>
                    </div>

                    <div class="steps">
                        <h3>Next Steps</h3>
                        <div class="step">
                            <span class="step-number">1</span>
                            Send payment via Wise or bank transfer
                        </div>
                        <div class="step">
                            <span class="step-number">2</span>
                            Go to <a href="{self.settings.FRONTEND_URL}/credits/requests">Credit Requests</a>
                        </div>
                        <div class="step">
                            <span class="step-number">3</span>
                            Upload your payment confirmation
                        </div>
                        <div class="step">
                            <span class="step-number">4</span>
                            Wait for admin approval
                        </div>
                    </div>

                    <p>If you have any questions, please reply to this email.</p>

                    <p>Best regards,<br>SEO Pro Team</p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send_email(user_email, subject, html)

    def send_payment_proof_notification(
        self,
        admin_email: str,
        user_email: str,
        invoice_number: str,
        credits: int,
        amount: float,
        proof_url: str,
        request_id: str
    ) -> bool:
        """Send notification to admin when user uploads payment proof."""
        subject = f"[SEO Pro] Payment Proof Uploaded - {invoice_number}"

        admin_url = f"{self.settings.FRONTEND_URL}/admin/credits"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #059669; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .details-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .detail {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #4F46E5; color: white; text-decoration: none; border-radius: 6px; }}
                .proof-link {{ display: inline-block; padding: 8px 16px; background: #E0E7FF; color: #4F46E5; text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Payment Proof Uploaded</h1>
                    <p>Action Required</p>
                </div>
                <div class="content">
                    <p>A user has uploaded payment proof for their credit request.</p>

                    <div class="details-box">
                        <h3>Request Details</h3>
                        <div class="detail">
                            <span>User:</span>
                            <strong>{user_email}</strong>
                        </div>
                        <div class="detail">
                            <span>Invoice:</span>
                            <strong>{invoice_number}</strong>
                        </div>
                        <div class="detail">
                            <span>Credits:</span>
                            <strong>{credits}</strong>
                        </div>
                        <div class="detail">
                            <span>Amount:</span>
                            <strong>${amount:.2f}</strong>
                        </div>
                        <div class="detail">
                            <span>Payment Proof:</span>
                            <a href="{proof_url}" class="proof-link">View Proof</a>
                        </div>
                    </div>

                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{admin_url}" class="button">Review in Dashboard</a>
                    </p>

                    <p>Request ID: <code>{request_id}</code></p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send_email(admin_email, subject, html)

    def send_credit_approval_notification(
        self,
        user_email: str,
        invoice_number: str,
        credits: int,
        new_balance: int
    ) -> bool:
        """Send notification to user when credits are approved."""
        subject = f"Credits Added - {invoice_number}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #059669; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .success-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; }}
                .credits {{ font-size: 48px; color: #059669; font-weight: bold; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #4F46E5; color: white; text-decoration: none; border-radius: 6px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Credits Added!</h1>
                </div>
                <div class="content">
                    <div class="success-box">
                        <p>Credits Added</p>
                        <p class="credits">+{credits}</p>
                        <p>New Balance: <strong>{new_balance}</strong></p>
                    </div>

                    <p>Your payment for invoice <strong>{invoice_number}</strong> has been confirmed and credits have been added to your account.</p>

                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{self.settings.FRONTEND_URL}/audits" class="button">Start Analyzing</a>
                    </p>

                    <p>Thank you for using SEO Pro!</p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send_email(user_email, subject, html)

    def send_credit_rejection_notification(
        self,
        user_email: str,
        invoice_number: str,
        reason: str
    ) -> bool:
        """Send notification to user when credit request is rejected."""
        subject = f"Credit Request Update - {invoice_number}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #DC2626; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .reason-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #DC2626; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #4F46E5; color: white; text-decoration: none; border-radius: 6px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Credit Request Update</h1>
                </div>
                <div class="content">
                    <p>We were unable to process your credit request for invoice <strong>{invoice_number}</strong>.</p>

                    <div class="reason-box">
                        <strong>Reason:</strong><br>
                        {reason}
                    </div>

                    <p>If you believe this is an error, please contact support or submit a new request.</p>

                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{self.settings.FRONTEND_URL}/credits" class="button">Request Credits Again</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send_email(user_email, subject, html)


# Singleton instance
_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
