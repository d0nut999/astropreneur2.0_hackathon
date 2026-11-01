"""Employees & leave: staffing overview, leave requests (human decides), handbook questions."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import require_role
from ..db import get_session
from ..models import Draft, DraftStatus, Employee, LeaveRequest, LeaveStatus, LeaveType, User, UserRole
from ..services import employees as E
from ..services import leave as L

router = APIRouter(prefix="/employees", tags=["employees"])
human = require_role(UserRole.RECRUITER, UserRole.ADMIN)


@router.get("/overview")
def overview(db: Session = Depends(get_session)):
    E.ensure_employees(db)
    data = L.overview(db)
    pending_ids = {r["email_id"] for r in data["requests"] if r["email_id"]} | {r["email_id"] for r in data["recent"] if r["email_id"]}
    drafts = db.exec(select(Draft).where(Draft.status == DraftStatus.PENDING, Draft.email_id != None)).all()  # noqa: E711
    emp_emails = {e.email for e in db.exec(select(Employee)).all()}
    leave_email_ids = {r.email_id for r in db.exec(select(LeaveRequest)).all() if r.email_id}
    data["pending_replies"] = [d.model_dump(mode="json") for d in drafts
                               if d.email_id in pending_ids or d.to_addr in emp_emails]
    data["leave_replies"] = [d for d in data["pending_replies"] if d["email_id"] in leave_email_ids]
    data["question_replies"] = [d for d in data["pending_replies"] if d["email_id"] not in leave_email_ids]
    return data


class Decide(BaseModel):
    action: str                       # approve | reject | propose | meeting
    note: str = ""
    alt_start: Optional[str] = None
    alt_end: Optional[str] = None


@router.post("/leave/{req_id}/decide")
def decide(req_id: int, body: Decide, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ HUMAN ONLY: approve / reject / propose other dates / offer a meeting. The reply is a draft to approve."""
    req = db.get(LeaveRequest, req_id)
    if not req:
        raise HTTPException(404, "Leave request not found")
    try:
        d = E.decide(db, req, body.action, user.id, body.note, body.alt_start, body.alt_end)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"id": req.id, "status": req.status.value, "draft_id": d.id,
            "message": "Saved. The reply to the employee is in the yellow box: read it and send it."}


class NewLeave(BaseModel):
    employee_id: int
    type: str = "annual"
    start: str
    end: Optional[str] = None


@router.post("/leave")
def create_leave(body: NewLeave, db: Session = Depends(get_session), user: User = Depends(human)):
    """HR enters a request received by phone or in person: it gets the same checks."""
    if not db.get(Employee, body.employee_id):
        raise HTTPException(404, "Employee not found")
    try:
        s = date.fromisoformat(body.start)
        e = date.fromisoformat(body.end or body.start)
    except ValueError:
        raise HTTPException(422, "Dates must be YYYY-MM-DD")
    if e < s:
        raise HTTPException(422, "The end date is before the start date")
    req = LeaveRequest(employee_id=body.employee_id, type=LeaveType(body.type if body.type in ("annual", "sick") else "annual"),
                       start=s, end=e, extracted_by="hr")
    db.add(req)
    db.commit()
    db.refresh(req)
    return L.request_json(db, req)


class Question(BaseModel):
    question: str
    employee_id: Optional[int] = None


@router.post("/ask")
def ask(body: Question, db: Session = Depends(get_session)):
    """Try the handbook assistant (nothing is sent)."""
    if not body.question.strip():
        raise HTTPException(422, "Write a question.")
    emp = db.get(Employee, body.employee_id) if body.employee_id else None
    return E.answer_question(db, body.question[:2000], emp)


@router.get("/handbook")
def handbook():
    return E.sections()
