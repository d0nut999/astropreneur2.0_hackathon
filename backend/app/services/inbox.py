"""Where emails come from. Three sources, same output format.

1. Demo files   : demo_data/emails/*.json            (always works, best for the jury demo)
2. Mailpit      : the fake mail server in docker-compose (emails sent to it arrive "live")
3. Real IMAP    : e.g. a test Gmail account (set IMAP_HOST/IMAP_USER/IMAP_PASSWORD in .env)

Every function returns a list of dicts:
{message_id, from_name, from_addr, to_addr, subject, body, received_at, attachments: [{filename, content(bytes)}]}
"""
import email
import imaplib
import json
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

import httpx

from ..config import settings

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _demo_dir() -> Path:
    p = Path(settings.demo_emails_dir)
    return p if p.is_absolute() else BACKEND_DIR / p


def load_demo_emails(now: datetime | None = None) -> list[dict]:
    """Read demo_data/emails/*.json. Dates are relative to now so the demo always looks fresh."""
    now = now or datetime.now()
    folder = _demo_dir()
    out = []
    for f in sorted(folder.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        attachments = []
        for a in data.get("attachments", []):
            src = (folder.parent / a["source"]).resolve()
            if src.exists():
                attachments.append({"filename": a["filename"], "content": src.read_bytes()})
        out.append({
            "message_id": f"demo-{f.stem}",
            # placeholders keep "today"/"tomorrow" correct whenever the demo runs
            "from_name": data.get("from_name", ""),
            "from_addr": data["from_addr"].lower(),
            "to_addr": data.get("to_addr", settings.hr_mailbox),
            "subject": _fill(data["subject"], now),
            "body": _fill(data["body"], now),
            "received_at": (now + timedelta(minutes=data.get("received_offset_minutes", 0))).replace(second=0, microsecond=0),
            "attachments": attachments,
        })
    return out


def _fill(text: str, now: datetime) -> str:
    """Replace demo placeholders: {in_2h} -> "20:00", {day_in_4} -> "Wednesday"."""
    in_2h = (now + timedelta(hours=2)).replace(minute=0)
    return (text.replace("{in_2h}", in_2h.strftime("%H:%M"))
                .replace("{day_in_4}", (now + timedelta(days=4)).strftime("%A")))


def fetch_from_mailpit(limit: int = 50) -> list[dict]:
    """Read messages from Mailpit's web API (http://localhost:8025)."""
    base = settings.mailpit_api_url.rstrip("/")
    out = []
    with httpx.Client(timeout=10) as client:
        listing = client.get(f"{base}/api/v1/messages", params={"limit": limit}).json()
        for summary in listing.get("messages", []):
            msg = client.get(f"{base}/api/v1/message/{summary['ID']}").json()
            attachments = []
            for att in msg.get("Attachments", []) or []:
                content = client.get(f"{base}/api/v1/message/{summary['ID']}/part/{att['PartID']}").content
                attachments.append({"filename": att.get("FileName", "attachment"), "content": content})
            sender = msg.get("From") or {}
            to = (msg.get("To") or [{}])[0]
            out.append({
                "message_id": msg.get("MessageID") or f"mailpit-{summary['ID']}",
                "from_name": sender.get("Name", ""),
                "from_addr": (sender.get("Address") or "").lower(),
                "to_addr": to.get("Address", ""),
                "subject": msg.get("Subject", ""),
                "body": msg.get("Text") or "",
                "received_at": _parse_iso(msg.get("Date") or summary.get("Created")),
                "attachments": attachments,
            })
    return out


def fetch_from_imap(limit: int = 30) -> list[dict]:
    """Read the latest messages from a real mailbox over IMAP (read-only)."""
    cls = imaplib.IMAP4_SSL if settings.imap_port == 993 else imaplib.IMAP4
    conn = cls(settings.imap_host, settings.imap_port)
    conn.login(settings.imap_user, settings.imap_password)
    conn.select("INBOX", readonly=True)  # read-only: we never delete or modify mail
    _, data = conn.search(None, "ALL")
    ids = data[0].split()[-limit:]
    out = []
    for i in ids:
        _, msg_data = conn.fetch(i, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        name, addr = parseaddr(msg.get("From", ""))
        body, attachments = "", []
        for part in msg.walk():
            disp = str(part.get("Content-Disposition", ""))
            if part.get_content_type() == "text/plain" and "attachment" not in disp and not body:
                body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
            elif "attachment" in disp and part.get_filename():
                attachments.append({"filename": _decode(part.get_filename()), "content": part.get_payload(decode=True)})
        try:
            received = parsedate_to_datetime(msg.get("Date")).astimezone().replace(tzinfo=None)
        except Exception:
            received = datetime.now()
        out.append({
            "message_id": msg.get("Message-ID", f"imap-{i.decode()}"),
            "from_name": _decode(name),
            "from_addr": addr.lower(),
            "to_addr": msg.get("To", ""),
            "subject": _decode(msg.get("Subject", "")),
            "body": body,
            "received_at": received,
            "attachments": attachments,
        })
    conn.logout()
    return out


def fetch_new_emails() -> tuple[list[dict], str]:
    """Use IMAP if configured, otherwise Mailpit. Returns (emails, source_name)."""
    if settings.imap_host and settings.imap_user:
        return fetch_from_imap(), "imap"
    return fetch_from_mailpit(), "mailpit"


def _decode(value: str) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return value or ""


def _parse_iso(value: str | None) -> datetime:
    if not value:
        return datetime.now()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
    except ValueError:
        return datetime.now()
