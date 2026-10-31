"""Follow-ups: who are we waiting for, and reminders (always drafted for HR approval)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ..auth import require_role
from ..config import settings
from ..db import get_session
from ..models import Application, User, UserRole
from ..services import followups as fu

router = APIRouter(prefix="/followups", tags=["followups"])
human = require_role(UserRole.RECRUITER, UserRole.ADMIN)


@router.get("")
@router.get("/")
def list_followups(db: Session = Depends(get_session)):
    items = fu.waiting_list(db)
    counts = {s: sum(i["state"] == s for i in items) for s in ("due", "your_call", "drafted", "waiting")}
    return {"items": items, "counts": counts, "after_hours": settings.followup_after_hours,
            "max_reminders": settings.followup_max_reminders, "demo_shift_hours": fu.demo_shift(),
            "dev": settings.app_env == "dev"}


def _app(app_id: int, db: Session) -> Application:
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    return app


@router.post("/{app_id}/remind")
def remind(app_id: int, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ Draft a reminder (with a new personal link). It is only sent when HR approves it."""
    try:
        d = fu.prepare_reminder(db, _app(app_id, db), actor=f"user:{user.id}")
    except fu.FollowUpError as e:
        raise HTTPException(400, str(e))
    return {"draft_id": d.id, "message": "Reminder drafted. Review and send it in the yellow box."}


@router.post("/remind_due")
def remind_due(db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ Draft reminders for everyone who is due (each one still needs its own approval)."""
    made = []
    for item in fu.waiting_list(db):
        if item["state"] == "due":
            d = fu.prepare_reminder(db, db.get(Application, item["application_id"]), actor=f"user:{user.id}")
            made.append(d.id)
    return {"drafted": len(made), "draft_ids": made,
            "message": f"{len(made)} reminder(s) drafted. Nothing is sent before you approve them."}


class CloseRequest(BaseModel):
    note: str = ""


@router.post("/{app_id}/close")
def close(app_id: int, req: CloseRequest, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ HUMAN ONLY: close the application after no reply (a polite email is drafted for approval)."""
    try:
        d = fu.close_no_response(db, _app(app_id, db), user.id, req.note)
    except fu.FollowUpError as e:
        raise HTTPException(400, str(e))
    return {"draft_id": d.id, "message": "Application closed. The polite closing email is in the yellow box."}


class ShiftRequest(BaseModel):
    hours: int


@router.post("/demo_clock")
def demo_clock(req: ShiftRequest, user: User = Depends(human)):
    """Dev only: pretend time passed (no data is changed) so the demo can show reminders becoming due."""
    if settings.app_env != "dev":
        raise HTTPException(403, "Demo clock is only available in dev mode.")
    fu.set_demo_shift(req.hours)
    return {"demo_shift_hours": fu.demo_shift()}
