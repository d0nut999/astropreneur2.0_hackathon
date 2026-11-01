"""HR calendar: one week of interviews, meetings, deadlines, interview blocks and free interview spots."""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..config import settings
from ..db import get_session
from ..models import Application, Candidate, Email, Event, EventStatus, InterviewSlot, Job, SlotStatus
from ..services import scheduler

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("")
@router.get("/")
def week(day: Optional[str] = None, db: Session = Depends(get_session)):
    """The week (Monday-Sunday) containing `day` (YYYY-MM-DD, default today)."""
    scheduler.expire_stale(db)
    ref = datetime.strptime(day, "%Y-%m-%d").date() if day else date.today()
    monday = ref - timedelta(days=ref.weekday())
    days = [monday + timedelta(days=i) for i in range(7)]
    in_week = {d.isoformat() for d in days}
    now = datetime.now()
    blocks = scheduler.blocks()

    items, all_day = [], []
    from ..services.leave import leave_on_day_for_calendar
    away = leave_on_day_for_calendar(db, days[0], days[-1])
    for slot in db.exec(select(InterviewSlot).where(InterviewSlot.status == SlotStatus.BOOKED)).all():
        if slot.start.date().isoformat() not in in_week:
            continue
        app = db.get(Application, slot.application_id)
        cand = db.get(Candidate, app.candidate_id) if app else None
        job = db.get(Job, app.job_id) if app else None
        items.append({
            "id": f"interview-{slot.id}", "kind": "interview", "status": "booked",
            "title": f"Final interview · Candidate #{slot.application_id:03d}",
            "who": cand.name if cand else "", "job": job.title if job else "",
            "start": slot.start.isoformat(), "end": slot.end.isoformat(),
            "location": settings.interview_location, "application_id": slot.application_id,
        })

    for ev in db.exec(select(Event).where(Event.status != EventStatus.DISMISSED)).all():
        if ev.date not in in_week:
            continue
        src = db.get(Email, ev.email_id)
        base = {
            "id": ev.id, "event_id": ev.id, "status": ev.status.value, "title": ev.title,
            "who": ", ".join(ev.attendees_json or []) or (src.from_name if src else ""),
            "location": ev.location, "email_id": ev.email_id,
            "email_subject": src.subject if src else "", "email_from": (src.from_name or src.from_addr) if src else "",
        }
        if ev.type == "deadline" or not ev.time:
            all_day.append({**base, "kind": ev.type.value, "date": ev.date})
            continue
        start = datetime.strptime(f"{ev.date} {ev.time}", "%Y-%m-%d %H:%M")
        clash = scheduler.interview_conflict(db, start)
        items.append({**base, "kind": "meeting", "start": start.isoformat(),
                      "end": (start + timedelta(minutes=60)).isoformat(),
                      "conflict": f"Clashes with the interview of Candidate #{clash.application_id:03d} at {clash.start:%H:%M}" if clash else None})

    free = [t for t in scheduler.free_times(db, horizon_days=21) if t.date().isoformat() in in_week]
    return {
        "week_start": monday.isoformat(),
        "now": now.isoformat(),
        "hours": {"start": 8, "end": 18},
        "lunch": {"start": settings.lunch_start, "end": settings.lunch_end},
        "days": [{
            "date": d.isoformat(), "weekday": d.strftime("%A"), "is_today": d == date.today(),
            "is_work_day": str(d.weekday()) in settings.work_days.split(","),
            "blocks": [{"start": f"{a:02d}:00", "end": f"{b:02d}:00"} for a, b in blocks.get(d.weekday(), [])],
            "away": [a for a in away if a["date"] == d.isoformat()],
        } for d in days],
        "items": sorted(items, key=lambda i: i["start"]),
        "all_day": all_day,
        "free_spots": [t.isoformat() for t in free],
        "summary": {
            "interviews": len([i for i in items if i["kind"] == "interview"]),
            "meetings": len([i for i in items if i["kind"] == "meeting"]),
            "to_confirm": len([i for i in items + all_day if i.get("status") == "suggested"]),
            "deadlines": len(all_day),
            "free_interview_spots": len(free),
            "clashes": len([i for i in items if i.get("conflict")]),
        },
        "settings": {"interview_minutes": settings.interview_minutes,
                     "max_interviews_per_day": settings.max_interviews_per_day,
                     "blocks_text": " · ".join(f"{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d]} {a}-{b}h"
                                               for d, spans in sorted(blocks.items()) for a, b in spans)},
    }
