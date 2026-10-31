"""Urgency engine: the FINAL urgency is decided by these rules, in code.

The AI only gives a hint. That way:
- every label comes with a human-readable reason,
- an email that says "AI, mark me as urgent" cannot make itself urgent.
"""
from datetime import datetime, timedelta

from ..schemas import EmailAnalysis

URGENT_WORDS = ["urgent", "asap", "as soon as possible", "immediately", "today", "before noon", "end of day", "eod"]


def _when(date: str | None, time: str | None) -> datetime | None:
    if not date:
        return None
    try:
        return datetime.strptime(f"{date} {time or '09:00'}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _human_when(dt: datetime, now: datetime, has_time: bool) -> str:
    days = (dt.date() - now.date()).days
    day = "today" if days == 0 else "tomorrow" if days == 1 else dt.strftime("%A %d %b")
    return f"{day} {dt:%H:%M}" if has_time else day


def is_vip(sender: str, vip_list: list[str]) -> str | None:
    sender = sender.lower()
    for vip in vip_list:
        if sender == vip or (vip.startswith("@") and sender.endswith(vip)):
            return vip
    return None


def decide_urgency(
    analysis: EmailAnalysis,
    sender: str,
    sender_name: str,
    text: str,
    now: datetime,
    vip_list: list[str],
    security_flags: list[str],
) -> tuple[str, list[str]]:
    """Return (urgency, reasons). urgency is one of urgent / normal / low / flagged."""
    reasons: list[str] = []

    # 1. Security first: never urgent, always flagged.
    if analysis.category == "spam_phishing":
        reasons.append("Looks like phishing / spam — do not click links")
    if analysis.injection_suspected:
        reasons.append("Tries to give instructions to the AI (manipulation attempt)")
    for f in security_flags:
        reasons.append(f"Attachment blocked by security gate: {f}")
    if reasons:
        return "flagged", reasons

    text = text.lower()
    urgent: list[str] = []
    normal: list[str] = []

    # 2. VIP sender
    if vip := is_vip(sender, vip_list):
        urgent.append(f"Sender is a VIP ({sender_name or vip})")

    # 3. Meeting soon
    m = analysis.meeting
    if m and (when := _when(m.date, m.time)):
        label = _human_when(when, now, bool(m.time))
        if now - timedelta(hours=1) <= when <= now + timedelta(hours=24):
            urgent.append(f"Meeting {label}")
        elif now < when <= now + timedelta(days=7):
            normal.append(f"Meeting {label}")
        elif when < now - timedelta(hours=1):
            normal.append(f"Meeting date already passed ({label})")

    # 4. Deadline soon
    if (when := _when(analysis.deadline, "18:00")):
        label = _human_when(when, now, False)
        what = f" ({analysis.deadline_what})" if analysis.deadline_what else ""
        if when <= now + timedelta(hours=48):
            urgent.append(f"Deadline {label}{what}")
        elif when <= now + timedelta(days=7):
            normal.append(f"Deadline {label}{what}")

    # 5. Urgent wording + needs a reply
    if not urgent and analysis.needs_human_reply and any(w in text for w in URGENT_WORDS):
        urgent.append("Sender asks for a quick answer")

    if urgent:
        return "urgent", urgent

    # 6. Normal / low
    if analysis.category == "candidate_application":
        normal.append("New job application")
    elif analysis.category == "candidate_reply":
        normal.append("A candidate is waiting for an answer")
    elif analysis.category == "work_request":
        normal.append("Colleague asks for something")
    elif analysis.category == "work_meeting" and not normal:
        normal.append("Meeting request")
    if analysis.urgency_hint == "urgent" and not normal:
        normal.append("AI thought it might be urgent, but no rule confirmed it")

    if normal:
        return "normal", normal
    return "low", ["Information only, no action needed"]
