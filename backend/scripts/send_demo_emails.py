#!/usr/bin/env python
"""Send the demo emails INTO Mailpit (the fake mail server), so they arrive "for real".

Usage (from the backend folder, with Mailpit running):
    python scripts/send_demo_emails.py            # send all demo emails
    python scripts/send_demo_emails.py 01 07      # send only the ones whose file name starts with 01 or 07

Then click "Sync inbox" in the dashboard (or POST /emails/sync).
"""
import os
import smtplib
import sys
from email.message import EmailMessage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings  # noqa: E402
from app.services.inbox import load_demo_emails  # noqa: E402


def main(prefixes: list[str]):
    emails = load_demo_emails()
    if prefixes:
        emails = [e for e in emails if any(e["message_id"].removeprefix("demo-").startswith(p) for p in prefixes)]
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        for e in emails:
            msg = EmailMessage()
            msg["From"] = f'{e["from_name"]} <{e["from_addr"]}>'
            msg["To"] = settings.hr_mailbox
            msg["Subject"] = e["subject"]
            msg.set_content(e["body"])
            for a in e["attachments"]:
                msg.add_attachment(a["content"], maintype="application", subtype="pdf", filename=a["filename"])
            smtp.send_message(msg)
            print(f"sent: {e['subject']}")
    print(f"\n{len(emails)} email(s) sent to Mailpit -> open http://localhost:8025, then click 'Sync inbox'.")


if __name__ == "__main__":
    main(sys.argv[1:])
