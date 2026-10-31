"""Public page where an advanced candidate picks an interview time (one-time link from the email)."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session

from ..config import settings
from ..db import get_session
from ..models import Application, Candidate, InterviewSlot, Job, OfferStatus
from ..services import scheduler
from ..services.security_gate import scan_text_for_injection

router = APIRouter(prefix="/schedule", tags=["schedule"])


class BookRequest(BaseModel):
    slot_id: int


class DeclineRequest(BaseModel):
    availability: str


def _offer(db: Session, token: str, allow_done: bool = False):
    scheduler.expire_stale(db)
    offer = scheduler.find_offer(db, token)
    if not offer or offer.status in (OfferStatus.DRAFT, OfferStatus.CANCELLED):
        raise HTTPException(404, "This link is not valid.")
    if offer.status == OfferStatus.EXPIRED:
        raise HTTPException(410, "These times are no longer reserved. Please contact the HR team.")
    if not allow_done and offer.status != OfferStatus.PENDING:
        raise HTTPException(410, "You already answered. Thank you!")
    return offer


@router.get("/{token}")
def get_offer(token: str, db: Session = Depends(get_session)):
    offer = _offer(db, token, allow_done=True)
    app = db.get(Application, offer.application_id)
    cand = db.get(Candidate, app.candidate_id)
    job = db.get(Job, app.job_id)
    slots = scheduler.offer_slots(db, offer)
    return {
        "first_name": (cand.name or "").split(" ")[0] if cand else "",
        "job_title": job.title if job else "",
        "status": offer.status.value,
        "location": settings.interview_location,
        "duration_minutes": settings.interview_minutes,
        "expires_at": offer.expires_at.isoformat(),
        "slots": [{"id": s.id, "start": s.start.isoformat(), "end": s.end.isoformat(), "status": s.status.value}
                  for s in slots],
    }


@router.post("/{token}/book")
def book_slot(token: str, req: BookRequest, db: Session = Depends(get_session)):
    offer = _offer(db, token)
    try:
        slot = scheduler.book(db, offer, req.slot_id)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"ok": True, "start": slot.start.isoformat(), "message": "Your interview is booked. See you soon!"}


@router.post("/{token}/decline")
def decline_slots(token: str, req: DeclineRequest, db: Session = Depends(get_session)):
    offer = _offer(db, token)
    note = (req.availability or "").strip()
    if len(note) < 5:
        raise HTTPException(422, "Please tell us when you are available (for example: 'Tuesday or Thursday afternoon').")
    if len(note) > 500:
        raise HTTPException(422, "Please keep it under 500 characters.")
    if scan_text_for_injection(note):
        note = "[removed: the text contained instructions for an AI system]"
    scheduler.decline(db, offer, note)
    return {"ok": True, "message": "Thank you! The HR team will send you new options soon."}


@router.get("/{token}/ics")
def candidate_ics(token: str, db: Session = Depends(get_session)):
    offer = _offer(db, token, allow_done=True)
    slot = next((s for s in scheduler.offer_slots(db, offer) if s.status.value == "booked"), None)
    if not slot:
        raise HTTPException(404, "No booked interview yet.")
    job = db.get(Job, db.get(Application, offer.application_id).job_id)
    return Response(scheduler.ics_for(slot, f"Interview - {job.title} - Fictional Company"), media_type="text/calendar",
                    headers={"Content-Disposition": 'attachment; filename="interview.ics"'})
