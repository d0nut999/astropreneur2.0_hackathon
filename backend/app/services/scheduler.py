"""Interview scheduling: propose 3 free slots from HR's calendar, hold them, book one, handle refusals.

HR's calendar = working hours (minus lunch)
                - meetings found in emails (suggested or confirmed: we never risk a clash)
                - interview slots already held or booked.
"""
import re
import secrets
from datetime import datetime, timedelta

from sqlmodel import Session, select

from ..audit import log_audit
from ..config import settings
from ..models import (
    Application, Candidate, Draft, DraftType, Event, EventStatus, EventType, InterviewSlot, Job, OfferStatus,
    ScheduleOffer, SlotStatus,
)
from .interview import hash_token

PREFERRED_HOURS = [10, 14, 11, 15, 9, 16]
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _work_days() -> set[int]:
    return {int(d) for d in settings.work_days.split(",") if d.strip().isdigit()}


def expire_stale(db: Session, now: datetime | None = None) -> None:
    """Offers nobody answered in time release their slots."""
    now = now or datetime.now()
    for offer in db.exec(select(ScheduleOffer).where(ScheduleOffer.status == OfferStatus.PENDING,
                                                     ScheduleOffer.expires_at < now)).all():
        offer.status = OfferStatus.EXPIRED
        db.add(offer)
        for s in db.exec(select(InterviewSlot).where(InterviewSlot.offer_id == offer.id,
                                                     InterviewSlot.status == SlotStatus.HELD)).all():
            s.status = SlotStatus.RELEASED
            db.add(s)
    db.commit()


def busy_intervals(db: Session) -> list[tuple[datetime, datetime, str]]:
    busy = []
    for ev in db.exec(select(Event).where(Event.type == EventType.MEETING, Event.status != EventStatus.DISMISSED)).all():
        if ev.date and ev.time:
            try:
                start = datetime.strptime(f"{ev.date} {ev.time}", "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            busy.append((start, start + timedelta(minutes=60), f"Meeting: {ev.title}"))
    for s in db.exec(select(InterviewSlot).where(InterviewSlot.status.in_([SlotStatus.HELD, SlotStatus.BOOKED]))).all():
        busy.append((s.start, s.end, f"Interview (application #{s.application_id:03d})"))
    return busy


def _overlaps(start: datetime, end: datetime, busy) -> bool:
    return any(start < b_end and b_start < end for b_start, b_end, _ in busy)


def interview_conflict(db: Session, start: datetime, end: datetime | None = None) -> InterviewSlot | None:
    """Is there a held/booked interview at this time? (used to warn about new meetings)"""
    end = end or start + timedelta(minutes=60)
    for s in db.exec(select(InterviewSlot).where(InterviewSlot.status.in_([SlotStatus.HELD, SlotStatus.BOOKED]))).all():
        if start < s.end and s.start < end:
            return s
    return None


def parse_availability(text: str, now: datetime) -> dict:
    """Very simple understanding of 'Tuesday or Wednesday afternoon', 'next week mornings', '05/11'."""
    t = (text or "").lower()
    days = {i for i, d in enumerate(WEEKDAYS) if re.search(rf"\b{d}\b", t)}
    parts = set()
    if "morning" in t or "matin" in t:
        parts.add("morning")
    if "afternoon" in t or "après-midi" in t or "apres-midi" in t:
        parts.add("afternoon")
    dates = set()
    for d, m in re.findall(r"\b(\d{1,2})/(\d{1,2})\b", t):
        try:
            dates.add(datetime(now.year, int(m), int(d)).date())
        except ValueError:
            pass
    return {"days": days, "parts": parts, "dates": dates, "next_week": "next week" in t}


def find_free_slots(db: Session, now: datetime | None = None, count: int = 3, prefs: dict | None = None,
                    horizon_days: int = 14) -> list[datetime]:
    """Up to `count` free slots, one per day, starting tomorrow, matching preferences when given."""
    now = now or datetime.now()
    busy = busy_intervals(db)
    length = timedelta(minutes=settings.interview_minutes)
    prefs = prefs or {}
    hours = list(PREFERRED_HOURS)
    if "morning" in prefs.get("parts", set()) and "afternoon" not in prefs.get("parts", set()):
        hours = [h for h in hours if h < settings.lunch_start]
    elif "afternoon" in prefs.get("parts", set()) and "morning" not in prefs.get("parts", set()):
        hours = [h for h in hours if h >= settings.lunch_end]
    hours = [h for h in hours if settings.work_day_start <= h and h + length.seconds / 3600 <= settings.work_day_end
             and not (settings.lunch_start <= h < settings.lunch_end)]

    first_day = (now + timedelta(days=1)).date()
    if prefs.get("next_week"):
        first_day = (now + timedelta(days=7 - now.weekday())).date()
    result: list[datetime] = []
    for offset in range(horizon_days):
        day = first_day + timedelta(days=offset)
        if day.weekday() not in _work_days():
            continue
        if prefs.get("dates") and day not in prefs["dates"]:
            continue
        if prefs.get("days") and not prefs.get("dates") and day.weekday() not in prefs["days"]:
            continue
        for h in hours:
            start = datetime(day.year, day.month, day.day, h, 0)
            if start > now and not _overlaps(start, start + length, busy):
                result.append(start)
                break
        if len(result) == count:
            break
    return result


def _human(dt: datetime) -> str:
    return dt.strftime("%A %d %B at %H:%M")


def create_offer(db: Session, app: Application, actor: str, prefs: dict | None = None,
                 round_no: int = 1) -> tuple[ScheduleOffer | None, Draft]:
    """Hold 3 slots and draft the email that proposes them (HR must approve before anything is sent)."""
    expire_stale(db)
    cand = db.get(Candidate, app.candidate_id)
    job = db.get(Job, app.job_id)
    first = (cand.name or "").split(" ")[0] if cand else "there"
    starts = find_free_slots(db, prefs=prefs)
    if len(starts) < 3 and prefs:  # preferences too narrow: complete with any free slot
        for s in find_free_slots(db, count=3):
            if s not in starts and len(starts) < 3:
                starts.append(s)
        starts.sort()

    if not starts:
        draft = Draft(application_id=app.id, to_addr=cand.email if cand else "", type=DraftType.REPLY,
                      subject=f"Good news about your application - {job.title}",
                      body=f"Hello {first},\n\nWe would like to invite you to a final interview. "
                           f"We will contact you shortly to agree on a time.\n\nBest regards,\nHR Team")
        db.add(draft)
        db.commit()
        db.refresh(draft)
        return None, draft

    token = secrets.token_urlsafe(32)
    offer = ScheduleOffer(application_id=app.id, token_hash=hash_token(token), round=round_no,
                          expires_at=datetime.now() + timedelta(hours=settings.slot_hold_hours))
    db.add(offer)
    db.commit()
    db.refresh(offer)
    length = timedelta(minutes=settings.interview_minutes)
    for s in starts:
        db.add(InterviewSlot(offer_id=offer.id, application_id=app.id, start=s, end=s + length))

    link = f"{settings.frontend_url.rstrip('/')}/schedule/{token}"
    options = "\n".join(f"  - {_human(s)} ({settings.interview_minutes} min)" for s in starts)
    intro = ("Thank you for your answers to our written interview. We were impressed and would like to invite you "
             "to a final interview with our team." if round_no == 1 else
             "Thank you for letting us know your availability. Here are new options for your interview.")
    body = (f"Hello {first},\n\n{intro}\n\nPlease choose the time that suits you best:\n{options}\n\n"
            f"Pick one here (personal link): {link}\n"
            f"If none of these work, the same page lets you tell us when you are available.\n\n"
            f"Location: {settings.interview_location}\n"
            f"These times are reserved for you for {settings.slot_hold_hours} hours.\n\nBest regards,\nHR Team")
    draft = Draft(application_id=app.id, to_addr=cand.email if cand else "", type=DraftType.REPLY,
                  subject=f"Choose your interview time - {job.title}", body=body)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    offer.draft_id = draft.id
    db.add(offer)
    db.commit()
    log_audit(db, actor=actor, action="propose_interview_slots", entity="application", entity_id=app.id,
              payload={"round": round_no, "slots": [s.isoformat() for s in starts]})
    return offer, draft


def activate_offer_for_draft(db: Session, draft: Draft) -> None:
    """Called when HR approved and sent the email: the candidate's link starts working now."""
    offer = db.exec(select(ScheduleOffer).where(ScheduleOffer.draft_id == draft.id)).first()
    if offer and offer.status == OfferStatus.DRAFT:
        offer.status = OfferStatus.PENDING
        offer.expires_at = datetime.now() + timedelta(hours=settings.slot_hold_hours)
        db.add(offer)
        db.commit()


def cancel_offer_for_draft(db: Session, draft: Draft) -> None:
    """HR rejected the email: release the held slots."""
    offer = db.exec(select(ScheduleOffer).where(ScheduleOffer.draft_id == draft.id)).first()
    if offer and offer.status == OfferStatus.DRAFT:
        offer.status = OfferStatus.CANCELLED
        db.add(offer)
        for s in db.exec(select(InterviewSlot).where(InterviewSlot.offer_id == offer.id)).all():
            s.status = SlotStatus.RELEASED
            db.add(s)
        db.commit()


def find_offer(db: Session, token: str) -> ScheduleOffer | None:
    if not token or len(token) > 200:
        return None
    return db.exec(select(ScheduleOffer).where(ScheduleOffer.token_hash == hash_token(token))).first()


def offer_slots(db: Session, offer: ScheduleOffer) -> list[InterviewSlot]:
    return sorted(db.exec(select(InterviewSlot).where(InterviewSlot.offer_id == offer.id)).all(), key=lambda s: s.start)


def book(db: Session, offer: ScheduleOffer, slot_id: int) -> InterviewSlot:
    slots = offer_slots(db, offer)
    chosen = next((s for s in slots if s.id == slot_id and s.status == SlotStatus.HELD), None)
    if not chosen:
        raise ValueError("This time is not available. Please choose one of the proposed times.")
    for s in slots:
        s.status = SlotStatus.BOOKED if s.id == chosen.id else SlotStatus.RELEASED
        db.add(s)
    offer.status = OfferStatus.BOOKED
    db.add(offer)
    db.commit()

    app = db.get(Application, offer.application_id)
    cand = db.get(Candidate, app.candidate_id)
    job = db.get(Job, app.job_id)
    first = (cand.name or "").split(" ")[0] if cand else "there"
    db.add(Draft(application_id=app.id, to_addr=cand.email if cand else "", type=DraftType.REPLY,
                 subject=f"Interview confirmed - {job.title}",
                 body=f"Hello {first},\n\nYour interview is confirmed for {_human(chosen.start)} "
                      f"({settings.interview_minutes} min).\nLocation: {settings.interview_location}\n\n"
                      f"See you soon,\nHR Team"))
    db.commit()
    log_audit(db, actor="candidate", action="book_interview", entity="application", entity_id=app.id,
              payload={"start": chosen.start.isoformat()})
    return chosen


def decline(db: Session, offer: ScheduleOffer, note: str) -> None:
    offer.status = OfferStatus.DECLINED
    offer.availability_note = note.strip()[:500]
    db.add(offer)
    for s in offer_slots(db, offer):
        s.status = SlotStatus.RELEASED
        db.add(s)
    db.commit()
    log_audit(db, actor="candidate", action="decline_interview_slots", entity="application",
              entity_id=offer.application_id, payload={"note": offer.availability_note[:200]})


def ics_for(slot: InterviewSlot, title: str) -> str:
    """A calendar file that Google Calendar / Outlook / Apple Calendar can import."""
    fmt = "%Y%m%dT%H%M%S"
    safe_title = re.sub(r"[\r\n,;]", " ", title)
    return "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//HireGuard//Interview//EN", "BEGIN:VEVENT",
        f"UID:hireguard-interview-{slot.id}@fictional-company.test",
        f"DTSTAMP:{datetime.now().strftime(fmt)}",
        f"DTSTART:{slot.start.strftime(fmt)}", f"DTEND:{slot.end.strftime(fmt)}",
        f"SUMMARY:{safe_title}",
        f"LOCATION:{re.sub(r'[,;]', ' ', settings.interview_location)}",
        "END:VEVENT", "END:VCALENDAR", "",
    ])


def scheduling_status(db: Session, app_id: int) -> dict | None:
    """Latest offer + slots for the HR candidate page."""
    expire_stale(db)
    offer = db.exec(select(ScheduleOffer).where(ScheduleOffer.application_id == app_id)
                    .order_by(ScheduleOffer.id.desc())).first()
    if not offer:
        return None
    draft = db.get(Draft, offer.draft_id) if offer.draft_id else None
    link = None
    if draft:
        m = re.search(r"https?://\S+/schedule/\S+", draft.body)
        link = m.group(0) if m else None
    return {
        "offer_id": offer.id, "status": offer.status.value, "round": offer.round,
        "availability_note": offer.availability_note, "expires_at": offer.expires_at.isoformat(),
        "draft_status": draft.status.value if draft else None, "link": link,
        "slots": [{"id": s.id, "start": s.start.isoformat(), "end": s.end.isoformat(), "status": s.status.value}
                  for s in offer_slots(db, offer)],
    }
