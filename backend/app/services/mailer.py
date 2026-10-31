"""Send emails via SMTP."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config import settings


def send_email(to: str, subject: str, body: str) -> bool:
    """
    Send email via SMTP.
    Stub: Returns True without actually sending (dev mode).
    Real implementation will connect to SMTP.
    """
    # TODO: Implement SMTP sending using smtplib
    # For now, just log to console
    print(f"[EMAIL] To: {to}")
    print(f"[EMAIL] Subject: {subject}")
    print(f"[EMAIL] Body: {body}")
    return True
