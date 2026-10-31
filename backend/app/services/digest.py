"""Daily digest: what the HR manager should look at first today. Built from the database (no AI)."""
from datetime import datetime, timedelta

from sqlmodel import Session, select

from ..models import Application, ApplicationStatus, Draft, DraftStatus, Email, EmailStatus, Event, EventStatus

URGENCY_ORDER = {"urgent": 0, "flagged": 1, "normal": 2, "low": 3}


def generate_digest(db: Session, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    emails = db.exec(select(Email).where(Email.status == EmailStatus.NEW)).all()
    urgent = sorted([e for e in emails if e.urgency == "urgent"], key=lambda e: e.received_at, reverse=True)
    flagged = [e for e in emails if e.urgency == "flagged"]
    needs_human = [e for e in emails if e.needs_human and e.urgency != "flagged"]

    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    events = db.exec(select(Event).where(Event.status != EventStatus.DISMISSED)).all()
    upcoming = sorted(
        [ev for ev in events if ev.date in (today, tomorrow)],
        key=lambda ev: (ev.date or "", ev.time or "99:99"),
    )

    pending_drafts = db.exec(select(Draft).where(Draft.status == DraftStatus.PENDING)).all()
    new_apps = db.exec(select(Application).where(
        Application.status.in_([ApplicationStatus.RECEIVED, ApplicationStatus.SCREENED, ApplicationStatus.SCORED])
    )).all()

    by_category: dict[str, int] = {}
    for e in emails:
        by_category[e.category] = by_category.get(e.category, 0) + 1

    # One readable sentence for the HR manager
    parts = []
    if urgent:
        parts.append(f"{len(urgent)} urgent email{'s' if len(urgent) > 1 else ''}")
    today_meetings = [ev for ev in upcoming if ev.date == today and ev.type == "meeting"]
    if today_meetings:
        first = today_meetings[0]
        parts.append(f"{len(today_meetings)} meeting{'s' if len(today_meetings) > 1 else ''} today"
                     f" (next: {first.title}{' at ' + first.time if first.time else ''})")
    apps_ok = [e for e in emails if e.category == "candidate_application" and e.urgency != "flagged"]
    if apps_ok:
        parts.append(f"{len(apps_ok)} new application{'s' if len(apps_ok) > 1 else ''}")
    if flagged:
        parts.append(f"{len(flagged)} suspicious email(s) blocked")
    waiting = db.exec(select(Application).where(Application.status == ApplicationStatus.EVALUATED)).all()
    if waiting:
        parts.append(f"{len(waiting)} candidate{'s' if len(waiting) > 1 else ''} waiting for your final decision")
    if pending_drafts:
        parts.append(f"{len(pending_drafts)} reply draft(s) waiting for your approval")
    summary = ("Today: " + ", ".join(parts) + ".") if parts else "Inbox is clear. Nothing needs your attention."

    return {
        # kept from the original stub so existing pages keep working
        "high_urgency_count": len(urgent),
        "needs_human_count": len(needs_human),
        "pending_approvals_count": len(pending_drafts),
        "pending_applications_count": len(new_apps),
        "summary": summary,
        # new
        "flagged_count": len(flagged),
        "awaiting_decision_count": len(waiting),
        "total_new_emails": len(emails),
        "by_category": by_category,
        "urgent_emails": [
            {"id": e.id, "from_name": e.from_name, "from_addr": e.from_addr, "subject": e.subject,
             "summary": e.summary, "reasons": e.urgency_reasons_json, "category": e.category,
             "received_at": e.received_at.isoformat()}
            for e in urgent[:6]
        ],
        "upcoming_events": [
            {"id": ev.id, "email_id": ev.email_id, "type": ev.type, "title": ev.title, "date": ev.date,
             "time": ev.time, "location": ev.location, "with_people": ev.attendees_json, "status": ev.status,
             "day": "today" if ev.date == today else "tomorrow"}
            for ev in upcoming
        ],
    }
