"""Email triage routes.

AI actions here only READ and RECORD. Anything that affects the outside world
(sending a reply, confirming a meeting) needs a logged-in human (✋).
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..audit import log_audit
from ..auth import require_role
from ..config import settings
from ..db import get_session
from ..models import Draft, DraftStatus, DraftType, Email, EmailStatus, Event, EventStatus, User, UserRole
from ..services.digest import URGENCY_ORDER
from ..services.drafter import draft_reply
from ..services.inbox import fetch_new_emails, load_demo_emails
from ..services.triage import process_incoming
from ..services import scheduler
from ..models import Application, InterviewSlot, SlotStatus

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


class SimulatedEmail(BaseModel):
    from_name: str = ""
    from_addr: str
    subject: str
    body: str


@router.post("/emails/simulate")
def simulate_email(req: SimulatedEmail, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ Dev only: pretend an email just arrived (to test or demo without a mail server)."""
    if settings.app_env != "dev":
        raise HTTPException(403, "Only available in dev")
    import uuid
    row = process_incoming(db, {
        "message_id": f"sim-{uuid.uuid4().hex}", "from_name": req.from_name.strip()[:100],
        "from_addr": req.from_addr.strip().lower()[:200], "to_addr": settings.hr_mailbox,
        "subject": req.subject.strip()[:300], "body": req.body[:6000],
        "received_at": datetime.now(), "attachments": [],
    })
    return _email_out(row)


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
    """Meetings and deadlines found in emails + interviews booked or reserved, soonest first."""
    scheduler.expire_stale(db)
    q = select(Event)
    if status:
        q = q.where(Event.status == status)
    out = []
    for ev in db.exec(q).all():
        src = db.get(Email, ev.email_id)
        conflict = None
        if ev.type == "meeting" and ev.date and ev.time and ev.status != EventStatus.DISMISSED:
            try:
                start = datetime.strptime(f"{ev.date} {ev.time}", "%Y-%m-%d %H:%M")
                slot = scheduler.interview_conflict(db, start)
                conflict = f"Clashes with the interview of Candidate #{slot.application_id:03d} at {slot.start:%H:%M}" if slot else None
            except ValueError:
                pass
        out.append({**ev.model_dump(), "with_people": ev.attendees_json, "conflict": conflict,
                    "email_subject": src.subject if src else "", "email_from": src.from_name or src.from_addr if src else ""})
    if not status or status in ("confirmed", "suggested"):
        for slot in db.exec(select(InterviewSlot).where(InterviewSlot.status.in_([SlotStatus.HELD, SlotStatus.BOOKED]))).all():
            out.append({
                "id": f"interview-{slot.id}", "type": "interview", "application_id": slot.application_id,
                "title": f"Final interview - Candidate #{slot.application_id:03d}",
                "date": slot.start.strftime("%Y-%m-%d"), "time": slot.start.strftime("%H:%M"),
                "location": settings.interview_location, "with_people": [],
                "status": "booked" if slot.status == SlotStatus.BOOKED else "reserved",
                "email_subject": "", "email_from": "", "conflict": None,
            })
    out.sort(key=lambda ev: (ev["date"] or "9999", ev["time"] or "99:99"))
    return out


def _decide_event(event_id: int, status: EventStatus, db: Session, user: User, force: bool = False):
    ev = db.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "Event not found")
    if status == EventStatus.CONFIRMED and not force and ev.type == "meeting" and ev.date and ev.time:
        try:
            slot = scheduler.interview_conflict(db, datetime.strptime(f"{ev.date} {ev.time}", "%Y-%m-%d %H:%M"))
        except ValueError:
            slot = None
        if slot:
            raise HTTPException(409, f"This meeting clashes with the interview of Candidate #{slot.application_id:03d} "
                                     f"at {slot.start:%H:%M}. Confirm anyway, or ask the sender for another time.")
    ev.status = status
    ev.decided_by = f"user:{user.id}"
    db.add(ev)
    db.commit()
    log_audit(db, actor=f"user:{user.id}", action=f"event_{status.value}", entity="event", entity_id=ev.id)
    db.refresh(ev)
    return ev.model_dump()


@router.post("/events/{event_id}/confirm")
def confirm_event(event_id: int, force: bool = False, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ HR confirms a meeting/deadline. Refused (409) if it clashes with an interview, unless force=true."""
    return _decide_event(event_id, EventStatus.CONFIRMED, db, user, force)


@router.post("/events/{event_id}/dismiss")
def dismiss_event(event_id: int, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ HR dismisses a suggestion."""
    return _decide_event(event_id, EventStatus.DISMISSED, db, user)
