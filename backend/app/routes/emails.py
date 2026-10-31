"""Email triage routes.

AI actions here only READ and RECORD. Anything that affects the outside world
(sending a reply, confirming a meeting) needs a logged-in human (✋).
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..audit import log_audit
from ..auth import require_role
from ..db import get_session
from ..models import Draft, DraftStatus, DraftType, Email, EmailStatus, Event, EventStatus, User, UserRole
from ..services.digest import URGENCY_ORDER
from ..services.drafter import draft_reply
from ..services.inbox import fetch_new_emails, load_demo_emails
from ..services.triage import process_incoming

router = APIRouter(tags=["emails"])
human = require_role(UserRole.RECRUITER, UserRole.ADMIN)


def _email_out(e: Email, full: bool = False) -> dict:
    out = {
        "id": e.id, "from_name": e.from_name, "from_addr": e.from_addr, "subject": e.subject,
        "received_at": e.received_at.isoformat(), "category": e.category, "summary": e.summary,
        "urgency": e.urgency, "urgency_reasons": e.urgency_reasons_json, "needs_human": e.needs_human,
        "injection_suspected": e.injection_suspected, "status": e.status,
        "has_attachments": bool(e.attachments_json), "application_id": e.application_id,
        "analysis_source": e.analysis_source,
    }
    if full:
        out.update({"body": e.body, "to_addr": e.to_addr, "attachments": e.attachments_json,
                    "injection_text": e.injection_text, "security_flags": e.security_flags_json})
    return out


def _import(db: Session, raws: list[dict]) -> dict:
    now = datetime.now()
    imported, skipped = [], 0
    for raw in raws:
        row = process_incoming(db, raw, now)
        if row:
            imported.append(row.id)
        else:
            skipped += 1
    return {"imported": len(imported), "already_had": skipped, "ids": imported}


@router.post("/emails/load_demo")
def load_demo(db: Session = Depends(get_session)):
    """Load the fictional demo emails from demo_data/emails (safe for the jury demo)."""
    return _import(db, load_demo_emails())


@router.post("/emails/sync")
def sync_inbox(db: Session = Depends(get_session)):
    """Fetch new emails from Mailpit (dev) or a real IMAP mailbox, then analyze them."""
    try:
        raws, source = fetch_new_emails()
    except Exception as e:
        raise HTTPException(503, f"Could not reach the mailbox: {e}. Is Mailpit running? Try 'Load demo emails' instead.")
    return {"source": source, **_import(db, raws)}


@router.get("/emails")
def list_emails(
    category: Optional[str] = None,
    urgency: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_session),
):
    """All emails, most important first."""
    q = select(Email)
    if category:
        q = q.where(Email.category == category)
    if urgency:
        q = q.where(Email.urgency == urgency)
    if status:
        q = q.where(Email.status == status)
    rows = db.exec(q).all()
    rows.sort(key=lambda e: (e.status == EmailStatus.HANDLED, URGENCY_ORDER.get(e.urgency, 9), -e.received_at.timestamp()))
    return [_email_out(e) for e in rows]


@router.get("/emails/{email_id}")
def get_email(email_id: int, db: Session = Depends(get_session)):
    e = db.get(Email, email_id)
    if not e:
        raise HTTPException(404, "Email not found")
    events = db.exec(select(Event).where(Event.email_id == email_id)).all()
    drafts = db.exec(select(Draft).where(Draft.email_id == email_id)).all()
    return {**_email_out(e, full=True), "events": [ev.model_dump() for ev in events],
            "drafts": [d.model_dump() for d in drafts]}


@router.post("/emails/{email_id}/draft_reply")
def create_draft_reply(email_id: int, db: Session = Depends(get_session)):
    """AI drafts a reply. It goes to the approval queue; nothing is sent."""
    e = db.get(Email, email_id)
    if not e:
        raise HTTPException(404, "Email not found")
    if e.urgency == "flagged":
        raise HTTPException(400, "This email was flagged as suspicious. HireGuard will not draft a reply to it.")
    draft, source = draft_reply(e, db)
    row = Draft(email_id=e.id, application_id=e.application_id, to_addr=e.from_addr,  # only the original sender
                type=DraftType.REPLY, subject=draft.subject, body=draft.body)
    db.add(row)
    db.commit()
    db.refresh(row)
    log_audit(db, actor="ai" if source == "ai" else "system", action="draft_reply", entity="draft",
              entity_id=row.id, payload={"email_id": e.id})
    db.refresh(row)
    return {**row.model_dump(), "source": source}


@router.post("/emails/{email_id}/handled")
def mark_handled(email_id: int, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ HR marks an email as handled."""
    e = db.get(Email, email_id)
    if not e:
        raise HTTPException(404, "Email not found")
    e.status = EmailStatus.HANDLED
    db.add(e)
    db.commit()
    log_audit(db, actor=f"user:{user.id}", action="mark_handled", entity="email", entity_id=e.id)
    return {"ok": True}


@router.get("/events")
def list_events(status: Optional[str] = None, db: Session = Depends(get_session)):
    """Meetings and deadlines found in emails, soonest first."""
    q = select(Event)
    if status:
        q = q.where(Event.status == status)
    rows = sorted(db.exec(q).all(), key=lambda ev: (ev.date or "9999", ev.time or "99:99"))
    out = []
    for ev in rows:
        src = db.get(Email, ev.email_id)
        out.append({**ev.model_dump(), "with_people": ev.attendees_json,
                    "email_subject": src.subject if src else "", "email_from": src.from_name or src.from_addr if src else ""})
    return out


def _decide_event(event_id: int, status: EventStatus, db: Session, user: User):
    ev = db.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "Event not found")
    ev.status = status
    ev.decided_by = f"user:{user.id}"
    db.add(ev)
    db.commit()
    log_audit(db, actor=f"user:{user.id}", action=f"event_{status.value}", entity="event", entity_id=ev.id)
    db.refresh(ev)
    return ev.model_dump()


@router.post("/events/{event_id}/confirm")
def confirm_event(event_id: int, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ HR confirms a meeting/deadline (adds it to the agenda)."""
    return _decide_event(event_id, EventStatus.CONFIRMED, db, user)


@router.post("/events/{event_id}/dismiss")
def dismiss_event(event_id: int, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ HR dismisses a suggestion."""
    return _decide_event(event_id, EventStatus.DISMISSED, db, user)
