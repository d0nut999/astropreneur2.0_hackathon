"""Candidate portal (public, protected by a one-time token).

The candidate only sees the questions, never the rubric or their score.
The link works only after HR approved and sent the invitation, expires, and can be used once.
"""
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ..audit import log_audit
from ..db import get_session
from ..models import Application, ApplicationStatus, Candidate, Job
from ..services.interview import find_session, questions_for
from ..services.security_gate import scan_text_for_injection
from ..state_machine import transition

router = APIRouter(prefix="/portal", tags=["portal"])
MAX_ANSWER_CHARS = 4000


class AnswersRequest(BaseModel):
    answers: dict[str, str]  # {question_id: answer}


def _open_session(db: Session, token: str):
    sub = find_session(db, token)
    if not sub:
        raise HTTPException(404, "This link is not valid.")
    if sub.used:
        raise HTTPException(410, "This link was already used. Thank you, your answers were received.")
    if sub.expires_at < datetime.now():
        raise HTTPException(410, "This link has expired. Please contact the HR team.")
    app = db.get(Application, sub.application_id)
    if not app or app.status != ApplicationStatus.INVITED:
        raise HTTPException(403, "This interview is not open yet.")
    return sub, app


@router.get("/{token}")
def get_portal_session(token: str, db: Session = Depends(get_session)):
    sub, app = _open_session(db, token)
    job = db.get(Job, app.job_id)
    cand = db.get(Candidate, app.candidate_id)
    qs = questions_for(db, app)
    return {
        "job_title": job.title if job else "",
        "first_name": (cand.name or "").split(" ")[0] if cand else "",
        "questions": [{"id": q.id, "text": q.text} for q in qs],  # no rubric for the candidate
        "expires_at": sub.expires_at.isoformat(),
        "token_remaining_hours": max(0, int((sub.expires_at - datetime.now()).total_seconds() // 3600)),
        "max_chars": MAX_ANSWER_CHARS,
    }


@router.post("/{token}/answers")
def submit_answers(token: str, req: AnswersRequest, db: Session = Depends(get_session)):
    sub, app = _open_session(db, token)
    qs = questions_for(db, app)
    answers, flags = [], []
    for q in qs:
        text = (req.answers.get(str(q.id)) or "").strip()
        if not text:
            raise HTTPException(422, f"Please answer every question (missing: question {qs.index(q) + 1}).")
        if len(text) > MAX_ANSWER_CHARS:
            raise HTTPException(422, f"Answer {qs.index(q) + 1} is too long (max {MAX_ANSWER_CHARS} characters).")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)  # strip control characters
        answers.append({"question_id": q.id, "question": q.text, "is_tailored": q.is_tailored, "answer": text})
        flags += scan_text_for_injection(text)

    sub.transcript_json = {"type": "written", "answers": answers, "submitted_at": datetime.now().isoformat(),
                           "injection_flags": flags}
    sub.used = True  # one-time link
    db.add(sub)
    db.commit()
    transition(db, app, ApplicationStatus.VIDEO_SUBMITTED, actor="candidate")
    log_audit(db, actor="candidate", action="submit_answers", entity="application", entity_id=app.id,
              payload={"answers": len(answers), "flags": len(flags)})
    return {"success": True, "message": "Thank you! Your answers were received. The HR team will get back to you."}


@router.post("/{token}/video")
def upload_video(token: str):
    """Video answers are not enabled in this version (written answers only)."""
    raise HTTPException(501, "Video answers are not enabled. Please use the written answers.")
