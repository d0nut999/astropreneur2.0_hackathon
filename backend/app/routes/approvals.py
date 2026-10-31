"""Approval queue: every outgoing email waits here for an HR click."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..audit import log_audit
from ..auth import require_role
from ..db import get_session
from ..models import Application, ApplicationStatus, Candidate, Draft, DraftStatus, DraftType, User, UserRole
from ..services.mailer import send_email
from ..services.scheduler import activate_offer_for_draft, cancel_offer_for_draft
from ..state_machine import transition

router = APIRouter(prefix="/approvals", tags=["approvals"])
human = require_role(UserRole.RECRUITER, UserRole.ADMIN)


class DraftEdit(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None


def _recipient(draft: Draft, db: Session) -> str:
    if draft.to_addr:
        return draft.to_addr
    if draft.application_id:
        app = db.get(Application, draft.application_id)
        cand = db.get(Candidate, app.candidate_id) if app else None
        if cand:
            return cand.email
    return ""


@router.get("")
@router.get("/")
def list_drafts(status: Optional[str] = "pending", db: Session = Depends(get_session)):
    """Drafts waiting for approval (use ?status= to see others, or status=all)."""
    q = select(Draft)
    if status and status != "all":
        q = q.where(Draft.status == status)
    rows = sorted(db.exec(q).all(), key=lambda d: d.created_at, reverse=True)
    return [{**d.model_dump(), "to_addr": _recipient(d, db)} for d in rows]


@router.put("/{draft_id}")
def edit_draft(draft_id: int, req: DraftEdit, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ HR edits the text before approving."""
    d = db.get(Draft, draft_id)
    if not d or d.status != DraftStatus.PENDING:
        raise HTTPException(404, "Pending draft not found")
    if req.subject is not None:
        d.subject = req.subject
    if req.body is not None:
        d.body = req.body
    db.add(d)
    db.commit()
    log_audit(db, actor=f"user:{user.id}", action="edit_draft", entity="draft", entity_id=d.id)
    db.refresh(d)
    return d.model_dump()


def _approve(d: Draft, db: Session, user: User) -> dict:
    to = _recipient(d, db)
    if not to:
        raise HTTPException(400, "No recipient for this draft")
    d.status = DraftStatus.APPROVED
    d.approved_by = user.id
    db.add(d)
    db.commit()
    log_audit(db, actor=f"user:{user.id}", action="approve_draft", entity="draft", entity_id=d.id)

    sent, how = send_email(to, d.subject, d.body)
    if sent:
        d.status = DraftStatus.SENT
        db.add(d)
        db.commit()
        log_audit(db, actor="system", action="email_sent", entity="draft", entity_id=d.id, payload={"to": to, "via": how})
        activate_offer_for_draft(db, d)  # if this email proposes interview times, the link works from now
        if d.type == DraftType.INVITE and d.application_id:
            app = db.get(Application, d.application_id)
            if app and app.status == ApplicationStatus.SHORTLISTED:
                transition(db, app, ApplicationStatus.INVITED, actor=f"user:{user.id}")
    message = "Sent" if how == "smtp" else "Mail server not running: email saved in backend/data/outbox"
    return {"id": d.id, "status": d.status, "sent": sent, "via": how, "to": to, "message": message}


@router.post("/{draft_id}/approve")
def approve_draft(draft_id: int, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ HR approves -> the email is sent now (and only now)."""
    d = db.get(Draft, draft_id)
    if not d or d.status != DraftStatus.PENDING:
        raise HTTPException(404, "Pending draft not found")
    return _approve(d, db, user)


class BulkApprove(BaseModel):
    ids: list[int]


@router.post("/bulk_approve")
def bulk_approve(req: BulkApprove, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ Approve and send the drafts HR selected (each one is listed and readable before; each one is audited)."""
    if not req.ids or len(req.ids) > 50:
        raise HTTPException(422, "Select between 1 and 50 drafts.")
    results = []
    for draft_id in dict.fromkeys(req.ids):
        d = db.get(Draft, draft_id)
        if not d or d.status != DraftStatus.PENDING:
            results.append({"id": draft_id, "ok": False, "message": "not pending"})
            continue
        try:
            r = _approve(d, db, user)
            results.append({"id": draft_id, "ok": r["sent"], "to": r["to"]})
        except HTTPException as e:
            results.append({"id": draft_id, "ok": False, "message": e.detail})
    sent = sum(r["ok"] for r in results)
    return {"sent": sent, "results": results, "message": f"{sent} email(s) sent."}


@router.post("/{draft_id}/reject")
def reject_draft(draft_id: int, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ HR rejects the draft. Nothing is sent."""
    d = db.get(Draft, draft_id)
    if not d or d.status != DraftStatus.PENDING:
        raise HTTPException(404, "Pending draft not found")
    d.status = DraftStatus.REJECTED
    db.add(d)
    db.commit()
    cancel_offer_for_draft(db, d)  # release interview times reserved for this email
    log_audit(db, actor=f"user:{user.id}", action="reject_draft", entity="draft", entity_id=d.id)
    return {"id": d.id, "status": d.status}
