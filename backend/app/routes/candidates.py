"""Candidate routes. NOTE: {candidate_id} in these URLs is the APPLICATION id
(one person can apply to several jobs; each application has its own score and status)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..audit import log_audit
from ..auth import require_role
from ..db import get_session
from ..models import Application, ApplicationStatus, Candidate, Email, Evaluation, Job, Score, User, UserRole
from ..schemas import DecisionRequest, ShortlistRequest
from ..services.scorer import score_application
from ..state_machine import StateTransitionError, transition

router = APIRouter(prefix="/candidates", tags=["candidates"])
human = require_role(UserRole.RECRUITER, UserRole.ADMIN)


def _latest_score(db: Session, app_id: int) -> Optional[Score]:
    return db.exec(select(Score).where(Score.application_id == app_id).order_by(Score.id.desc())).first()


def _row(db: Session, app: Application) -> dict:
    cand = db.get(Candidate, app.candidate_id)
    s = _latest_score(db, app.id)
    crit = (s.criteria_json.get("criteria", []) if s else [])
    return {
        "id": app.id,                       # application id
        "candidate_id": app.candidate_id,
        "alias": f"Candidate #{app.id:03d}",  # for blind review
        "name": cand.name if cand else "?",
        "email": cand.email if cand else "",
        "job_id": app.job_id,
        "status": app.status.value,
        "total": s.total if s else None,
        "scored_by": (s.criteria_json.get("source") if s else None),
        "summary": (s.criteria_json.get("summary", "") if s else ""),
        "strengths": (s.criteria_json.get("strengths", []) if s else []),
        "flags": (s.criteria_json.get("flags", []) if s else []) + app.security_flags_json.get("flags", []),
        "criteria": [{"label": c["label"], "score": c["score"], "weight": c["weight"]} for c in crit],
        "created_at": app.created_at.isoformat(),
    }


@router.get("")
@router.get("/")
def list_candidates(job_id: int, db: Session = Depends(get_session)):
    """Ranked list for one job: scored first (highest total first), then unscored, then quarantined."""
    apps = db.exec(select(Application).where(Application.job_id == job_id)).all()
    rows = [_row(db, a) for a in apps]
    rows.sort(key=lambda r: (r["status"] == "QUARANTINED", r["total"] is None, -(r["total"] or 0)))
    rank = 0
    for r in rows:
        if r["total"] is not None and r["status"] != "QUARANTINED":
            rank += 1
            r["rank"] = rank
        else:
            r["rank"] = None
    return rows


@router.get("/{candidate_id}")
def get_candidate_detail(candidate_id: int, db: Session = Depends(get_session)):
    """Full profile: identity, job, latest score with evidence, security flags, anonymized CV, source email."""
    app = db.get(Application, candidate_id)
    if not app:
        raise HTTPException(404, "Application not found")
    cand = db.get(Candidate, app.candidate_id)
    job = db.get(Job, app.job_id)
    s = _latest_score(db, app.id)
    ev = db.exec(select(Evaluation).where(Evaluation.application_id == app.id).order_by(Evaluation.id.desc())).first()
    email = db.exec(select(Email).where(Email.application_id == app.id)).first()
    return {
        **_row(db, app),
        "job": {"id": job.id, "title": job.title} if job else None,
        "score": ({**s.criteria_json, "total": s.total, "model": s.model, "created_at": s.created_at.isoformat()} if s else None),
        "security": app.security_flags_json,
        "anonymized_cv": app.anonymized_profile_json.get("text", ""),
        "removed_personal_info": len(app.anonymized_profile_json.get("removed", [])),
        "evaluation": ev.model_dump() if ev else None,
        "email_id": email.id if email else None,
    }


@router.post("/{candidate_id}/score")
def rescore(candidate_id: int, db: Session = Depends(get_session)):
    """(Re)score this application. Quarantined CVs are refused."""
    app = db.get(Application, candidate_id)
    if not app:
        raise HTTPException(404, "Application not found")
    try:
        s = score_application(db, app)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"total": s.total, "status": app.status.value}


@router.post("/{candidate_id}/shortlist")
def shortlist_candidate(candidate_id: int, req: ShortlistRequest = None, db: Session = Depends(get_session),
                        user: User = Depends(human)):
    """✋ HUMAN ONLY: shortlist a scored candidate."""
    app = db.get(Application, candidate_id)
    if not app:
        raise HTTPException(404, "Application not found")
    try:
        transition(db, app, ApplicationStatus.SHORTLISTED, actor=f"user:{user.id}")
    except StateTransitionError as e:
        raise HTTPException(400, str(e))
    return {"id": app.id, "status": app.status.value}


@router.post("/{candidate_id}/decision")
def make_decision(candidate_id: int, req: DecisionRequest, db: Session = Depends(get_session),
                  user: User = Depends(human)):
    """✋ HUMAN ONLY: final decision (used after the interview step)."""
    app = db.get(Application, candidate_id)
    if not app:
        raise HTTPException(404, "Application not found")
    try:
        transition(db, app, ApplicationStatus.DECIDED, actor=f"user:{user.id}")
    except StateTransitionError as e:
        raise HTTPException(400, str(e))
    log_audit(db, actor=f"user:{user.id}", action="decision", entity="application", entity_id=app.id,
              payload={"decision": req.recommendation})
    return {"id": app.id, "status": app.status.value, "decision": req.recommendation}
