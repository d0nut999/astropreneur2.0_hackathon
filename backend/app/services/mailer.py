"""Send emails via SMTP. Only ever called from the approval route (after an HR click)."""
import smtplib
from email.mime.text import MIMEText

from ..config import settings


def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns False if the SMTP server is unreachable."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = settings.hr_mailbox
    msg["To"] = to
    msg["Subject"] = subject
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.send_message(msg)
        return True
    except OSError as e:
        print(f"[mailer] could not send to {to}: {e}")
        return False
