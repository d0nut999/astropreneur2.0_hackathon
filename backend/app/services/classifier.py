"""Email classifier: AI first, offline rules as a safety net.

The AI only RETURNS JSON. It cannot act. The urgency is decided later by
rules in app/services/urgency.py, so a manipulative email cannot make itself urgent.
"""
import re
from datetime import datetime, timedelta
from pathlib import Path

from sqlmodel import Session

from ..config import settings
from ..llm import LLMError, complete_json
from ..schemas import EmailAnalysis, MeetingInfo
from .security_gate import scan_text_for_injection

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "classify_email.md"
PROMPT_VERSION = "classify_v1"


def company_domain() -> str:
    return settings.hr_mailbox.split("@")[-1].lower()


def analyze_email(email: dict, now: datetime, db: Session | None = None) -> tuple[EmailAnalysis, str]:
    """Return (analysis, source) where source is "ai" or "rules"."""
    try:
        analysis = _analyze_with_ai(email, now, db)
        source = "ai"
    except LLMError as e:
        print(f"[classifier] AI unavailable, using offline rules: {e}")
        analysis = analyze_with_rules(email, now)
        source = "rules"

    # Code-level injection scan always runs, whatever the AI said.
    hits = scan_text_for_injection(f"{email.get('subject', '')}\n{email.get('body', '')}")
    if hits and not analysis.injection_suspected:
        analysis.injection_suspected = True
        analysis.injection_text = hits[0]
    return analysis, source


def _analyze_with_ai(email: dict, now: datetime, db: Session | None) -> EmailAnalysis:
    system = PROMPT_PATH.read_text(encoding="utf-8")
    received = email["received_at"]
    attachments = ", ".join(a.get("filename", "") for a in email.get("attachments", [])) or "none"
    user = (
        f"Current date/time: {now:%A %Y-%m-%d %H:%M}\n"
        f"Email received: {received:%A %Y-%m-%d %H:%M}\n"
        f"HR company domain: {company_domain()}\n\n"
        f"<email>\n"
        f"From: {email.get('from_name', '')} <{email['from_addr']}>\n"
        f"Subject: {email['subject']}\n"
        f"Attachments: {attachments}\n\n"
        f"{email['body'][:6000]}\n"
        f"</email>"
    )
    return complete_json(
        task="classify_email",
        system=system,
        user=user,
        schema=EmailAnalysis,
        prompt_version=PROMPT_VERSION,
        db=db,
    )


# ------------------------------------------------------------------
# Offline rules (used when no API key / API down). Simple but reliable.
# ------------------------------------------------------------------
PHISHING_WORDS = [
    "verify your account", "account is locked", "account has been locked", "suspended",
    "confirm your password", "reset your password", "click here", "unusual sign-in",
    "you have won", "gift card", "bank details",
]
APPLICATION_WORDS = ["apply", "application", "candidature", "my cv", "my resume", "resume attached", "cv attached", "position"]
CANDIDATE_REPLY_WORDS = ["interview", "my answers", "answers to", "reschedule", "salary", "my application", "availability"]
MEETING_WORDS = ["meeting", "meet", "call", "réunion", "appointment", "sync", "catch up", "1:1"]
REQUEST_WORDS = ["please send", "could you", "can you", "please prepare", "please review", "by friday", "deadline", "before", "asap", "needed by"]
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _has(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def find_date(text: str, base: datetime) -> str | None:
    """Find a date in text relative to the email date (today, tomorrow, weekday, 2026-11-02, 02/11)."""
    t = text.lower()
    if m := re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", t):
        return m.group(0)
    if m := re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(20\d{2}))?\b", t):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3) or base.year)
        try:
            return datetime(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            pass
    if "today" in t or "this afternoon" in t or "tonight" in t or "this morning" in t:
        return base.strftime("%Y-%m-%d")
    if "tomorrow" in t:
        return (base + timedelta(days=1)).strftime("%Y-%m-%d")
    for i, day in enumerate(WEEKDAYS):
        if re.search(rf"\b{day}\b", t):
            delta = (i - base.weekday()) % 7 or 7
            if "next " + day in t and delta < 7:
                delta += 7
            return (base + timedelta(days=delta)).strftime("%Y-%m-%d")
    if "next week" in t:
        return (base + timedelta(days=7 - base.weekday())).strftime("%Y-%m-%d")
    return None


def find_time(text: str) -> str | None:
    t = text.lower()
    if m := re.search(r"\b([01]?\d|2[0-3])[:h]([0-5]\d)\b", t):
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    if m := re.search(r"\b(1[0-2]|0?[1-9])\s?(am|pm)\b", t):
        h = int(m.group(1)) % 12 + (12 if m.group(2) == "pm" else 0)
        return f"{h:02d}:00"
    if m := re.search(r"\b([01]?\d|2[0-3])h\b", t):
        return f"{int(m.group(1)):02d}:00"
    if "noon" in t:
        return "12:00"
    return None


def _first_sentences(body: str, limit: int = 200) -> str:
    text = " ".join(body.split())
    for greet in ("Hi,", "Hello,", "Dear HR,", "Dear Sir/Madam,", "Hi team,", "Hello team,"):
        if text.startswith(greet):
            text = text[len(greet):].strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for p in parts:
        if len(out) + len(p) > limit:
            break
        out += p + " "
    return (out or text[:limit]).strip()


def analyze_with_rules(email: dict, now: datetime) -> EmailAnalysis:
    subject = email.get("subject", "")
    body = email.get("body", "")
    text = f"{subject}\n{body}".lower()
    sender = email["from_addr"].lower()
    internal = sender.endswith("@" + company_domain())
    has_cv = any(a.get("filename", "").lower().endswith((".pdf", ".docx")) for a in email.get("attachments", []))
    received = email["received_at"]

    date = find_date(text, received)
    time = find_time(text)
    meeting = None
    deadline = None
    deadline_what = ""

    if _has(text, PHISHING_WORDS) and not internal:
        category = "spam_phishing"
    elif not internal and has_cv and _has(text, APPLICATION_WORDS + ["cv", "resume"]):
        category = "candidate_application"
    elif not internal and _has(text, CANDIDATE_REPLY_WORDS):
        category = "candidate_reply"
    elif _has(text, MEETING_WORDS) and (date or time):
        category = "work_meeting"
        meeting = MeetingInfo(title=subject[:80], date=date, time=time,
                              with_people=[email.get("from_name") or sender])
    elif _has(text, REQUEST_WORDS):
        category = "work_request"
        deadline = date
        deadline_what = subject[:80] if date else ""
    else:
        category = "work_info"

    summary = _first_sentences(body)
    who = email.get("from_name") or sender
    return EmailAnalysis(
        category=category,
        summary=f"{who}: {summary}",
        needs_human_reply=category in {"candidate_reply", "work_meeting", "work_request"},
        urgency_hint="urgent" if _has(text, ["urgent", "asap", "today"]) else "normal",
        meeting=meeting,
        deadline=deadline,
        deadline_what=deadline_what,
    )
