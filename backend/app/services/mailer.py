"""Send emails via SMTP. Only ever called from the approval route (after an HR click).

If no mail server is running (e.g. Mailpit not started), the email is saved as a .eml
file in backend/data/outbox/ so the demo never gets stuck.
"""
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from ..config import settings

OUTBOX = Path(__file__).resolve().parents[2] / "data" / "outbox"


def send_email(to: str, subject: str, body: str) -> tuple[bool, str]:
    """Send a plain-text email. Returns (delivered, how) where how is "smtp" or "outbox"."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = settings.hr_mailbox
    msg["To"] = to
    msg["Subject"] = subject
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as smtp:
            smtp.send_message(msg)
        return True, "smtp"
    except OSError as e:
        print(f"[mailer] SMTP not reachable ({e}); saving to outbox instead")
        OUTBOX.mkdir(parents=True, exist_ok=True)
        safe_to = "".join(ch if ch.isalnum() else "_" for ch in to)[:40]
        path = OUTBOX / f"{datetime.now():%Y%m%d_%H%M%S}_{safe_to}.eml"
        path.write_bytes(msg.as_bytes())
        return True, "outbox"
