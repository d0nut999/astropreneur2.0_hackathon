"""Interview scheduling with INTERVIEW BLOCKS and FIRST COME, FIRST SERVED booking.

- HR defines interview blocks (e.g. Tue & Thu 14:00-17:00). Interviews only happen there,
  so the rest of the calendar stays free.
- Nothing is reserved in advance: every invited candidate sees the times that are free RIGHT NOW.
- Booking is atomic: if two candidates click the same time, only the first one gets it;
  the other is offered the closest free times.
- Free = inside a block, not during lunch, no meeting found in emails (suggested or confirmed),
  no other booked interview, max interviews per day not reached, at least `min_notice_hours` ahead.
"""
import re
import secrets
import threading
from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from ..audit import log_audit
from ..config import settings
from ..models import (
    Application, Candidate, Draft, DraftType, Event, EventStatus, EventType, InterviewSlot, Job, OfferStatus,
    ScheduleOffer, SlotStatus,
)
from .interview import hash_token

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_booking_lock = threading.Lock()  # one booking at a time -> no double booking


class SlotTaken(Exception):
    """The requested time is no longer free."""

    def __init__(self, message: str, alternatives: list[datetime]):
        super().__init__(message)
        self.alternatives = alternatives


# ---------------------------------------------------------------- configuration helpers
def blocks() -> dict[int, list[tuple[int, int]]]:
    """{weekday: [(start_hour, end_hour), ...]} from settings.interview_blocks."""
    out: dict[int, list[tuple[int, int]]] = {}
    for part in settings.interview_blocks.split(","):
        m = re.match(r"\s*(\d)\s*:\s*(\d{1,2})\s*-\s*(\d{1,2})\s*$", part)
        if m:
            out.setdefault(int(m.group(1)), []).append((int(m.group(2)), int(m.group(3))))
    return out


def _length() -> timedelta:
    return timedelta(minutes=settings.interview_minutes)


def block_starts(day: date) -> list[datetime]:
    """All possible interview start times on a day (inside blocks, outside lunch)."""
    starts = []
    for b_start, b_end in blocks().get(day.weekday(), []):
        t = datetime(day.year, day.month, day.day, b_start)
        end = datetime(day.year, day.month, day.day, b_end)
        while t + _length() <= end:
            in_lunch = settings.lunch_start <= t.hour < settings.lunch_end
            if not in_lunch:
                starts.append(t)
            t += _length()
    return starts


# ---------------------------------------------------------------- busy time
def busy_intervals(db: Session) -> list[tuple[datetime, datetime, str]]:
    busy = []
    for ev in db.exec(select(Event).where(Event.type == EventType.MEETING, Event.status != EventStatus.DISMISSED)).all():
        if ev.date and ev.time:
            try:
                start = datetime.strptime(f"{ev.date} {ev.time}", "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            busy.append((start, start + timedelta(minutes=60), f"Meeting: {ev.title}"))
    for s in db.exec(select(InterviewSlot).where(InterviewSlot.status == SlotStatus.BOOKED)).all():
        busy.append((s.start, s.end, f"Interview (application #{s.application_id:03d})"))
    return busy


def _overlaps(start: datetime, end: datetime, busy) -> bool:
    return any(start < b_end and b_start < end for b_start, b_end, _ in busy)


def interview_conflict(db: Session, start: datetime, end: datetime | None = None) -> InterviewSlot | None:
    """Booked interview at this time? (used to warn about new meetings)"""
    end = end or start + timedelta(minutes=60)
    for s in db.exec(select(InterviewSlot).where(InterviewSlot.status == SlotStatus.BOOKED)).all():
        if start < s.end and s.start < end:
            return s
    return None


def _booked_per_day(db: Session) -> dict[date, int]:
    counts: dict[date, int] = {}
    for s in db.exec(select(InterviewSlot).where(InterviewSlot.status == SlotStatus.BOOKED)).all():
        counts[s.start.date()] = counts.get(s.start.date(), 0) + 1
    return counts


def is_free(db: Session, start: datetime, now: datetime | None = None) -> bool:
    now = now or datetime.now()
    if start < now + timedelta(hours=settings.min_notice_hours) or start not in block_starts(start.date()):
        return False
    if _booked_per_day(db).get(start.date(), 0) >= settings.max_interviews_per_day:
        return False
    return not _overlaps(start, start + _length(), busy_intervals(db))


# ---------------------------------------------------------------- finding free times
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


def free_times(db: Session, now: datetime | None = None, limit: int | None = None, prefs: dict | None = None,
               horizon_days: int = 21) -> list[datetime]:
    """Free interview times, soonest first, matching preferences when given."""
    now = now or datetime.now()
    prefs = prefs or {}
    busy = busy_intervals(db)
    per_day = _booked_per_day(db)
    earliest = now + timedelta(hours=settings.min_notice_hours)
    first_day = now.date()
    if prefs.get("next_week"):
        first_day = (now + timedelta(days=7 - now.weekday())).date()
    out = []
    for offset in range(horizon_days):
        day = first_day + timedelta(days=offset)
        if prefs.get("dates") and day not in prefs["dates"]:
            continue
        if prefs.get("days") and not prefs.get("dates") and day.weekday() not in prefs["days"]:
            continue
        taken_today = per_day.get(day, 0)
        for start in block_starts(day):
            if taken_today >= settings.max_interviews_per_day:
                break
            if "morning" in prefs.get("parts", set()) and "afternoon" not in prefs.get("parts", set()) and start.hour >= 12:
                continue
            if "afternoon" in prefs.get("parts", set()) and "morning" not in prefs.get("parts", set()) and start.hour < 12:
                continue
            if start >= earliest and not _overlaps(start, start + _length(), busy):
                out.append(start)
                if limit and len(out) >= limit:
                    return out
    return out


def times_for_offer(db: Session, offer: ScheduleOffer, limit: int | None = None) -> list[datetime]:
    """Live free times for one candidate: their preferences first, then any other free time."""
    limit = limit or settings.times_shown_to_candidate
    prefs = parse_availability(offer.availability_note, datetime.now()) if offer.availability_note else None
    times = free_times(db, limit=limit, prefs=prefs) if prefs else []
    for t in free_times(db, limit=limit * 2):
        if len(times) >= limit:
            break
        if t not in times:
            times.append(t)
    return sorted(times)[:limit]


def nearest_free(db: Session, around: datetime, count: int = 3) -> list[datetime]:
    candidates = free_times(db, horizon_days=28)
    return sorted(candidates, key=lambda t: abs((t - around).total_seconds()))[:count]


def capacity(db: Session, days: int = 7) -> int:
    """How many interview spots are still free in the next `days` days."""
    now = datetime.now()
    return len([t for t in free_times(db, horizon_days=days) if t < now + timedelta(days=days)])


def _human(dt: datetime) -> str:
    return dt.strftime("%A %d %B at %H:%M")


# ---------------------------------------------------------------- offers
def expire_stale(db: Session, now: datetime | None = None) -> None:
    """Links older than offer_link_days stop working (no time was reserved, so nothing to free)."""
    now = now or datetime.now()
    for offer in db.exec(select(ScheduleOffer).where(ScheduleOffer.status == OfferStatus.PENDING,
                                                     ScheduleOffer.expires_at < now)).all():
        offer.status = OfferStatus.EXPIRED
        db.add(offer)
    # legacy: older versions reserved ("held") times; release them
    for s in db.exec(select(InterviewSlot).where(InterviewSlot.status == SlotStatus.HELD)).all():
        s.status = SlotStatus.RELEASED
        db.add(s)
    db.commit()


def create_offer(db: Session, app: Application, actor: str, availability_note: str = "",
                 round_no: int = 1) -> tuple[ScheduleOffer | None, Draft]:
    """Draft the email inviting the candidate to pick a time (HR approves before it is sent)."""
    expire_stale(db)
    cand = db.get(Candidate, app.candidate_id)
    job = db.get(Job, app.job_id)
    first = (cand.name or "").split(" ")[0] if cand else "there"

    token = secrets.token_urlsafe(32)
    offer = ScheduleOffer(application_id=app.id, token_hash=hash_token(token), round=round_no,
                          availability_note=availability_note,
                          expires_at=datetime.now() + timedelta(days=settings.offer_link_days))
    db.add(offer)
    db.commit()
    db.refresh(offer)
    preview = times_for_offer(db, offer, limit=3)
    link = f"{settings.frontend_url.rstrip('/')}/schedule/{token}"
    intro = ("Thank you for your answers to our written interview. We were impressed and would like to invite you "
             "to a final interview with our team." if round_no == 1 else
             "Thank you for letting us know your availability. Here are new options for your interview.")
    if preview:
        options = "\n".join(f"  - {_human(t)}" for t in preview)
        times_text = (f"Some of the times available right now:\n{options}\n\n"
                      f"Please choose here (personal link, live availability): {link}\n"
                      f"Times are given on a first-come, first-served basis, so we recommend booking soon.")
    else:
        times_text = (f"Please choose a time here (personal link, live availability): {link}\n"
                      f"New times are added regularly.")
    body = (f"Hello {first},\n\n{intro}\n\n{times_text}\n"
            f"If none of the times work, the same page lets you tell us when you are available.\n\n"
            f"Duration: {settings.interview_minutes} minutes. Location: {settings.interview_location}\n\n"
            f"Best regards,\nHR Team")
    draft = Draft(application_id=app.id, to_addr=cand.email if cand else "", type=DraftType.REPLY,
                  subject=f"Choose your interview time - {job.title}", body=body)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    offer.draft_id = draft.id
    db.add(offer)
    db.commit()
    log_audit(db, actor=actor, action="invite_to_schedule", entity="application", entity_id=app.id,
              payload={"round": round_no, "preview": [t.isoformat() for t in preview]})
    return offer, draft


def activate_offer_for_draft(db: Session, draft: Draft) -> None:
    """HR approved and sent the email: the candidate's link works from now."""
    offer = db.exec(select(ScheduleOffer).where(ScheduleOffer.draft_id == draft.id)).first()
    if offer and offer.status == OfferStatus.DRAFT:
        offer.status = OfferStatus.PENDING
        offer.expires_at = datetime.now() + timedelta(days=settings.offer_link_days)
        db.add(offer)
        db.commit()


def cancel_offer_for_draft(db: Session, draft: Draft) -> None:
    offer = db.exec(select(ScheduleOffer).where(ScheduleOffer.draft_id == draft.id)).first()
    if offer and offer.status == OfferStatus.DRAFT:
        offer.status = OfferStatus.CANCELLED
        db.add(offer)
        db.commit()


def find_offer(db: Session, token: str) -> ScheduleOffer | None:
    if not token or len(token) > 200:
        return None
    return db.exec(select(ScheduleOffer).where(ScheduleOffer.token_hash == hash_token(token))).first()


def latest_offer(db: Session, app_id: int) -> ScheduleOffer | None:
    return db.exec(select(ScheduleOffer).where(ScheduleOffer.application_id == app_id)
                   .order_by(ScheduleOffer.id.desc())).first()


def booked_slot(db: Session, app_id: int) -> InterviewSlot | None:
    return db.exec(select(InterviewSlot).where(InterviewSlot.application_id == app_id,
                                               InterviewSlot.status == SlotStatus.BOOKED)).first()


# ---------------------------------------------------------------- booking (atomic)
def book_time(db: Session, app_id: int, start: datetime, actor: str, offer: ScheduleOffer | None = None) -> InterviewSlot:
    """Book `start` for this application, or raise SlotTaken with the closest alternatives."""
    with _booking_lock:
        db.expire_all()  # read the latest state, not a cached one
        if booked_slot(db, app_id):
            raise SlotTaken("This candidate already has a booked interview.", [])
        if not is_free(db, start):
            raise SlotTaken("Sorry, this time was just taken or is not available.", nearest_free(db, start))
        offer = offer or latest_offer(db, app_id)
        slot = InterviewSlot(offer_id=offer.id if offer else 0, application_id=app_id, start=start,
                             end=start + _length(), status=SlotStatus.BOOKED)
        db.add(slot)
        if offer:
            offer.status = OfferStatus.BOOKED
            db.add(offer)
        db.commit()
        db.refresh(slot)

    app = db.get(Application, app_id)
    cand = db.get(Candidate, app.candidate_id)
    job = db.get(Job, app.job_id)
    first = (cand.name or "").split(" ")[0] if cand else "there"
    db.add(Draft(application_id=app.id, to_addr=cand.email if cand else "", type=DraftType.REPLY,
                 subject=f"Interview confirmed - {job.title}",
                 body=f"Hello {first},\n\nYour interview is confirmed for {_human(slot.start)} "
                      f"({settings.interview_minutes} min).\nLocation: {settings.interview_location}\n\n"
                      f"See you soon,\nHR Team"))
    db.commit()
    log_audit(db, actor=actor, action="book_interview", entity="application", entity_id=app.id,
              payload={"start": slot.start.isoformat()})
    return slot


def decline(db: Session, offer: ScheduleOffer, note: str) -> None:
    offer.status = OfferStatus.DECLINED
    offer.availability_note = note.strip()[:500]
    db.add(offer)
    db.commit()
    log_audit(db, actor="candidate", action="decline_interview_times", entity="application",
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
    """Latest offer + booking + live free times for the HR candidate page."""
    expire_stale(db)
    offer = latest_offer(db, app_id)
    slot = booked_slot(db, app_id)
    if not offer and not slot:
        reqs = requests_for(db, app_id)
        return {"offer_id": None, "status": "none", "round": 0, "availability_note": "", "expires_at": None,
                "draft_status": None, "link": None, "booked": None, "live_times": [], "requests": reqs} if reqs else None
    draft = db.get(Draft, offer.draft_id) if offer and offer.draft_id else None
    link = None
    if draft:
        m = re.search(r"https?://\S+/schedule/\S+", draft.body)
        link = m.group(0) if m else None
    live = [t.isoformat() for t in times_for_offer(db, offer)] if offer and offer.status == OfferStatus.PENDING else []
    return {
        "offer_id": offer.id if offer else None,
        "status": "booked" if slot else (offer.status.value if offer else "none"),
        "round": offer.round if offer else 1,
        "availability_note": offer.availability_note if offer else "",
        "expires_at": offer.expires_at.isoformat() if offer else None,
        "draft_status": draft.status.value if draft else None,
        "link": link,
        "booked": {"id": slot.id, "start": slot.start.isoformat(), "end": slot.end.isoformat()} if slot else None,
        "live_times": live,
        "requests": requests_for(db, app_id),
    }


# ---------------------------------------------------------------- candidate emails about time
def scheduling_application(db: Session, from_addr: str) -> Application | None:
    """The application of this sender if they are an advanced candidate without a booked interview."""
    from ..models import Decision

    cand = db.exec(select(Candidate).where(Candidate.email == (from_addr or "").lower())).first()
    if not cand:
        return None
    for app in db.exec(select(Application).where(Application.candidate_id == cand.id)).all():
        dec = db.exec(select(Decision).where(Decision.application_id == app.id).order_by(Decision.id.desc())).first()
        if dec and dec.decision == "advance" and not booked_slot(db, app.id):
            return app
    return None


def link_time_request(db: Session, email, analysis) -> "TimeRequest | None":
    """If an email comes from a candidate who is being scheduled, record the time they ask for."""
    from ..models import TimeRequest
    from .classifier import find_date, find_time

    app = scheduling_application(db, email.from_addr)
    for app in ([app] if app else []):
        text = f"{email.subject}\n{email.body}"
        start = None
        if analysis.meeting and analysis.meeting.date and analysis.meeting.time:
            try:
                start = datetime.strptime(f"{analysis.meeting.date} {analysis.meeting.time}", "%Y-%m-%d %H:%M")
            except ValueError:
                start = None
        if not start:
            d, t = find_date(text, email.received_at), find_time(text)
            if d and t:
                start = datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
        req = TimeRequest(application_id=app.id, email_id=email.id, requested_start=start, text=email.body[:500])
        db.add(req)
        if not email.application_id:
            email.application_id = app.id
        reasons = list(email.urgency_reasons_json or [])
        if start:
            free = is_free(db, start)
            reasons.insert(0, f"Candidate asks for an interview on {start:%a %d %b %H:%M}"
                              f" ({'free - can be booked' if free else 'not available'})")
        else:
            reasons.insert(0, "Candidate writes about interview availability")
        email.urgency_reasons_json = reasons
        email.needs_human = True
        if email.urgency == "low":
            email.urgency = "normal"
        db.add(email)
        db.commit()
        db.refresh(req)
        return req
    return None


def requests_for(db: Session, app_id: int) -> list[dict]:
    from ..models import TimeRequest

    out = []
    for r in db.exec(select(TimeRequest).where(TimeRequest.application_id == app_id, TimeRequest.status == "open")
                     .order_by(TimeRequest.id.desc())).all():
        free = is_free(db, r.requested_start) if r.requested_start else False
        if r.requested_start:
            alts = [] if free else nearest_free(db, r.requested_start)
        else:
            alts = free_times(db, limit=3, prefs=parse_availability(r.text, datetime.now())) or free_times(db, limit=3)
        out.append({"id": r.id, "email_id": r.email_id, "text": r.text,
                    "requested_start": r.requested_start.isoformat() if r.requested_start else None,
                    "free": free, "alternatives": [a.isoformat() for a in alts],
                    "created_at": r.created_at.isoformat()})
    return out
