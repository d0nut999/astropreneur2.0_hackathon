"""Follow-ups: candidates we are waiting for.

Two situations are tracked:
  - "answers":  invited to the written interview, no answers yet
  - "schedule": invited to pick an interview time, no time booked yet

Rules (in code, no AI):
  - a reminder becomes DUE after `followup_after_hours` of silence since our last email
  - each reminder contains a NEW personal link (only hashes are stored, so old links cannot be re-sent);
    the new link only starts working when HR approves and sends the reminder
  - after `followup_max_reminders` reminders, HireGuard stops suggesting reminders: HR decides
    (for example: close the application with a polite email)
Nothing is ever sent automatically: every reminder is a draft that HR approves.
"""
import secrets
from datetime import datetime, timedelta

from sqlmodel import Session, select

from ..audit import log_audit
from ..config import settings
from ..models import (
    Application, ApplicationStatus, Candidate, Decision, Draft, DraftStatus, DraftType, Job, OfferStatus,
    ScheduleOffer, SentEmail, VideoSubmission,
)
from .interview import hash_token
from .scheduler import _human, booked_slot, expire_stale, times_for_offer

# Demo clock (dev only): lets a 5-minute demo show what happens "3 days later" without touching any data.
_demo_shift_hours = 0


def demo_shift() -> int:
    return _demo_shift_hours


def set_demo_shift(hours: int) -> None:
    global _demo_shift_hours
    _demo_shift_hours = max(0, min(int(hours), 24 * 30))


def now() -> datetime:
    return datetime.now() + timedelta(hours=_demo_shift_hours)


# ---------------------------------------------------------------- recording sent emails
def kind_of(db: Session, draft: Draft) -> str:
    offer = db.exec(select(ScheduleOffer).where(ScheduleOffer.draft_id == draft.id)).first()
    if offer:
        return "schedule_reminder" if draft.type == DraftType.REMINDER else "schedule"
    if draft.type == DraftType.INVITE:
        return "invite"
    if draft.type == DraftType.REMINDER:
        return "answers_reminder"
    if draft.type == DraftType.REJECTION:
        return "closing"
    return "other"


def record_sent(db: Session, draft: Draft) -> None:
    """Called when an approved email was sent. Also switches on the new link of an answers reminder."""
    db.add(SentEmail(draft_id=draft.id, application_id=draft.application_id, kind=kind_of(db, draft),
                     sent_at=now()))  # demo clock aware, so a demo stays consistent
    # the link validity starts now (demo clock aware: without a demo shift this is the real time)
    link = db.exec(select(VideoSubmission).where(VideoSubmission.path == f"reminder:{draft.id}")).first()
    if link:
        link.expires_at = now() + timedelta(hours=settings.portal_token_ttl_hours)
        db.add(link)
    offer = db.exec(select(ScheduleOffer).where(ScheduleOffer.draft_id == draft.id)).first()
    if offer and _demo_shift_hours:
        offer.expires_at = now() + timedelta(days=settings.offer_link_days)
        db.add(offer)
    db.commit()


def on_draft_rejected(db: Session, draft: Draft) -> None:
    """HR rejected a reminder: its new link never becomes active; a reminder's scheduling offer is removed."""
    if draft.type != DraftType.REMINDER:
        return
    offer = db.exec(select(ScheduleOffer).where(ScheduleOffer.draft_id == draft.id)).first()
    if offer:
        db.delete(offer)
    link = db.exec(select(VideoSubmission).where(VideoSubmission.path == f"reminder:{draft.id}")).first()
    if link:
        link.used = True
        db.add(link)
    db.commit()


def _sent(db: Session, app_id: int, kinds: tuple[str, ...]) -> list[SentEmail]:
    return list(db.exec(select(SentEmail).where(SentEmail.application_id == app_id, SentEmail.kind.in_(kinds))
                        .order_by(SentEmail.sent_at)).all())


def _pending_reminder(db: Session, app_id: int) -> Draft | None:
    return db.exec(select(Draft).where(Draft.application_id == app_id, Draft.type == DraftType.REMINDER,
                                       Draft.status == DraftStatus.PENDING)).first()


def _latest_decision(db: Session, app_id: int) -> Decision | None:
    return db.exec(select(Decision).where(Decision.application_id == app_id).order_by(Decision.id.desc())).first()


def _open_offer(db: Session, app_id: int) -> ScheduleOffer | None:
    """The offer we are waiting on: sent (pending) or expired without an answer."""
    offer = db.exec(select(ScheduleOffer).where(ScheduleOffer.application_id == app_id,
                                                ScheduleOffer.status != OfferStatus.CANCELLED)
                    .order_by(ScheduleOffer.id.desc())).first()
    if offer and offer.status == OfferStatus.DRAFT:
        # a scheduling reminder (or a new invitation) is waiting for approval: look at the one before it
        prev = db.exec(select(ScheduleOffer).where(ScheduleOffer.application_id == app_id,
                                                   ScheduleOffer.id < offer.id,
                                                   ScheduleOffer.status.in_([OfferStatus.PENDING, OfferStatus.EXPIRED]))
                       .order_by(ScheduleOffer.id.desc())).first()
        return prev if (prev and _pending_reminder(db, app_id)) else None
    return offer if offer and offer.status in (OfferStatus.PENDING, OfferStatus.EXPIRED) else None


# ---------------------------------------------------------------- who are we waiting for?
def item_for(db: Session, app: Application, at: datetime | None = None) -> dict | None:
    at = at or now()
    kind, first_kinds, reminder_kind, link_expires = None, (), "", None

    if app.status == ApplicationStatus.INVITED:
        kind, first_kinds, reminder_kind = "answers", ("invite",), "answers_reminder"
        link = db.exec(select(VideoSubmission).where(VideoSubmission.application_id == app.id,
                                                     VideoSubmission.used == False)  # noqa: E712
                       .order_by(VideoSubmission.expires_at.desc())).first()
        link_expires = link.expires_at if link else None
        fallback = db.exec(select(Draft).where(Draft.application_id == app.id, Draft.type == DraftType.INVITE,
                                               Draft.status == DraftStatus.SENT)).first()
    elif app.status == ApplicationStatus.DECIDED:
        dec = _latest_decision(db, app.id)
        if not dec or dec.decision != "advance" or booked_slot(db, app.id):
            return None
        offer = _open_offer(db, app.id)
        if not offer:
            return None
        kind, first_kinds, reminder_kind = "schedule", ("schedule",), "schedule_reminder"
        link_expires = offer.expires_at
        fallback = db.get(Draft, offer.draft_id) if offer.draft_id else None
        if fallback and fallback.status != DraftStatus.SENT:
            fallback = None
    else:
        return None

    firsts = _sent(db, app.id, first_kinds)
    reminders = _sent(db, app.id, (reminder_kind,))
    contacts = firsts + reminders
    if contacts:
        last_contact = max(c.sent_at for c in contacts)
        first_contact = min(c.sent_at for c in contacts)
    elif fallback:  # data created before follow-ups existed
        last_contact = first_contact = fallback.created_at
    else:
        return None  # the first email was never sent: nothing to follow up yet

    cand = db.get(Candidate, app.candidate_id)
    job = db.get(Job, app.job_id)
    waited_h = (at - last_contact).total_seconds() / 3600
    pending = _pending_reminder(db, app.id)
    max_r = settings.followup_max_reminders
    if pending:
        state = "drafted"
    elif waited_h < settings.followup_after_hours:
        state = "waiting"
    elif len(reminders) >= max_r:
        state = "your_call"
    else:
        state = "due"
    expired = bool(link_expires and link_expires < at)
    label = "written interview answers" if kind == "answers" else "an interview time"
    reason = {
        "waiting": (f"Reminder {len(reminders)} sent {'less than an hour' if waited_h < 1 else _ago(waited_h)} ago. "
                    if reminders else f"Waiting for {label}. ")
                   + f"Next reminder possible in {_ago(max(1, settings.followup_after_hours - waited_h))} if still no reply.",
        "due": f"No reply for {_ago(waited_h)}" + (" and the link has expired." if expired else "."),
        "your_call": f"No reply after {len(reminders)} reminders. Your call: close the application or wait.",
        "drafted": "A reminder is waiting for your approval.",
    }[state]
    return {
        "application_id": app.id,
        "candidate_name": cand.name if cand else "",
        "alias": f"Candidate #{app.id:03d}",
        "job_title": job.title if job else "",
        "kind": kind,
        "waiting_for": label,
        "state": state,
        "reason": reason,
        "first_contact": first_contact.isoformat(),
        "last_contact": last_contact.isoformat(),
        "hours_waiting": round(waited_h, 1),
        "last_contact_ago": "less than an hour ago" if waited_h < 1 else f"{_ago(waited_h)} ago",
        "reminders_sent": len(reminders),
        "max_reminders": max_r,
        "link_expires_at": link_expires.isoformat() if link_expires else None,
        "link_expired": expired,
        "pending_draft_id": pending.id if pending else None,
        "can_remind": state == "due",
        "can_close": state != "drafted" and (len(reminders) > 0 or state == "your_call"),
    }


def _ago(hours: float) -> str:
    return f"{round(hours)} hours" if hours < 48 else f"{round(hours / 24)} days"


ORDER = {"due": 0, "your_call": 1, "drafted": 2, "waiting": 3}


def waiting_list(db: Session) -> list[dict]:
    expire_stale(db)  # real clock: the demo clock never changes data
    apps = db.exec(select(Application).where(
        Application.status.in_([ApplicationStatus.INVITED, ApplicationStatus.DECIDED]))).all()
    items = [i for i in (item_for(db, a) for a in apps) if i]
    return sorted(items, key=lambda i: (ORDER[i["state"]], -i["hours_waiting"]))


# ---------------------------------------------------------------- drafting reminders
class FollowUpError(ValueError):
    pass


def prepare_reminder(db: Session, app: Application, actor: str) -> Draft:
    item = item_for(db, app)
    if not item:
        raise FollowUpError("We are not waiting for anything from this candidate.")
    if item["pending_draft_id"]:
        return db.get(Draft, item["pending_draft_id"])
    if item["reminders_sent"] >= settings.followup_max_reminders:
        raise FollowUpError(f"Already reminded {item['reminders_sent']} times. Decide instead "
                            f"(for example close the application).")
    if item["state"] == "waiting":
        raise FollowUpError(f"Not due yet: {item['reason']}")

    cand = db.get(Candidate, app.candidate_id)
    job = db.get(Job, app.job_id)
    first = (cand.name or "").split(" ")[0] if cand and cand.name else "there"
    last = item["reminders_sent"] + 1 >= settings.followup_max_reminders
    deadline = (datetime.now() + timedelta(days=3)).strftime("%A %d %B")
    token = secrets.token_urlsafe(32)
    sent_on = datetime.fromisoformat(item["first_contact"]).strftime("%d %B")

    draft = Draft(application_id=app.id, to_addr=cand.email if cand else "", type=DraftType.REMINDER,
                  subject="", body="")
    db.add(draft)
    db.commit()
    db.refresh(draft)

    if item["kind"] == "answers":
        # new one-time link, switched on only when HR sends this reminder
        db.add(VideoSubmission(application_id=app.id, path=f"reminder:{draft.id}", token_hash=hash_token(token),
                               expires_at=datetime.now() - timedelta(seconds=1)))
        link = f"{settings.frontend_url.rstrip('/')}/portal/{token}"
        draft.subject = f"{'Last reminder' if last else 'Reminder'}: your written interview - {job.title}"
        body = (f"Hello {first},\n\n"
                f"On {sent_on} we invited you to a short written interview for the {job.title} position, "
                f"and we have not received your answers yet. We would still be glad to hear from you.\n\n"
                f"Here is a new personal link (valid {settings.portal_token_ttl_hours} hours, can be used once):\n"
                f"{link}\n\n")
    else:
        old = _open_offer(db, app.id)
        offer = ScheduleOffer(application_id=app.id, token_hash=hash_token(token), round=old.round if old else 1,
                              availability_note=old.availability_note if old else "", draft_id=draft.id,
                              expires_at=datetime.now() + timedelta(days=settings.offer_link_days))
        db.add(offer)
        db.commit()
        preview = times_for_offer(db, offer, limit=3)
        link = f"{settings.frontend_url.rstrip('/')}/schedule/{token}"
        draft.subject = f"{'Last reminder' if last else 'Reminder'}: choose your interview time - {job.title}"
        times = ("Some of the times available right now:\n" + "\n".join(f"  - {_human(t)}" for t in preview) + "\n\n"
                 if preview else "")
        body = (f"Hello {first},\n\n"
                f"On {sent_on} we invited you to choose a time for your final interview for the {job.title} "
                f"position, and you have not picked one yet.\n\n{times}"
                f"Please choose here (new personal link, live availability): {link}\n"
                f"If none of the times work, the same page lets you tell us when you are available.\n\n")
    if last:
        body += (f"If we do not hear from you by {deadline}, we will assume you are no longer available "
                 f"and close your application. ")
    body += ("If you are no longer interested, a short reply is enough - no problem at all.\n\n"
             "Best regards,\nHR Team")
    draft.body = body
    db.add(draft)
    db.commit()
    db.refresh(draft)
    log_audit(db, actor=actor, action="prepare_reminder", entity="application", entity_id=app.id,
              payload={"draft_id": draft.id, "kind": item["kind"], "number": item["reminders_sent"] + 1,
                       "hours_waiting": item["hours_waiting"]})
    return draft


CLOSING_SUBJECT = "Your application - {job}"
CLOSING_BODY = ("Hello {first},\n\nWe have not heard back from you, so we have closed your application for the "
                "{job} position for now. If this was a mistake or your situation changes, simply reply to this "
                "email and we will be happy to pick things up again.\n\nWe wish you all the best.\n\n"
                "Best regards,\nHR Team")


def close_no_response(db: Session, app: Application, user_id: int, note: str) -> Draft:
    """✋ HR closes the application after no reply. Saved as a human decision; a polite email is drafted."""
    from ..state_machine import transition
    item = item_for(db, app)
    if not item:
        raise FollowUpError("We are not waiting for anything from this candidate.")
    if app.status == ApplicationStatus.INVITED:
        transition(db, app, ApplicationStatus.DECIDED, actor=f"user:{user_id}")
        for link in db.exec(select(VideoSubmission).where(VideoSubmission.application_id == app.id,
                                                          VideoSubmission.used == False)).all():  # noqa: E712
            link.used = True
            db.add(link)
    for offer in db.exec(select(ScheduleOffer).where(ScheduleOffer.application_id == app.id, ScheduleOffer.status.in_(
            [OfferStatus.PENDING, OfferStatus.EXPIRED, OfferStatus.DRAFT]))).all():
        offer.status = OfferStatus.CANCELLED
        db.add(offer)
    for d in db.exec(select(Draft).where(Draft.application_id == app.id, Draft.status == DraftStatus.PENDING)).all():
        d.status = DraftStatus.REJECTED
        db.add(d)
    reason = note.strip() or f"No response after {item['reminders_sent']} reminder(s)."
    db.add(Decision(application_id=app.id, decision="reject", ai_recommendation="None", agrees_with_ai=True,
                    note=f"Closed - no response. {reason}"[:1000], decided_by=f"user:{user_id}"))
    cand = db.get(Candidate, app.candidate_id)
    job = db.get(Job, app.job_id)
    first = (cand.name or "").split(" ")[0] if cand and cand.name else "there"
    draft = Draft(application_id=app.id, to_addr=cand.email if cand else "", type=DraftType.REJECTION,
                  subject=CLOSING_SUBJECT.format(job=job.title), body=CLOSING_BODY.format(first=first, job=job.title))
    db.add(draft)
    db.commit()
    db.refresh(draft)
    log_audit(db, actor=f"user:{user_id}", action="close_no_response", entity="application", entity_id=app.id,
              payload={"reminders_sent": item["reminders_sent"], "kind": item["kind"], "note": reason[:200]})
    return draft
