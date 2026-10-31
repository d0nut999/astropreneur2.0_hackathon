"""Candidate routes. NOTE: {candidate_id} in these URLs is the APPLICATION id
(one person can apply to several jobs; each application has its own score and status)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session, select

from ..audit import log_audit
from ..auth import require_role
from ..db import get_session
import re

from ..models import (
    Application, ApplicationStatus, Candidate, Decision, Draft, DraftType, Email, Evaluation, Job, Score, User,
    UserRole, VideoSubmission,
)
from ..schemas import DecisionRequest, ShortlistRequest
from ..services.evaluator import evaluate_interview
from ..services.interview import prepare_invitation, questions_for
from ..services import scheduler
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
        "recommendation": _latest_eval(db, app.id).recommendation if _latest_eval(db, app.id) else None,
        "decision": _latest_decision(db, app.id).decision if _latest_decision(db, app.id) else None,
    }


def _latest_eval(db: Session, app_id: int) -> Optional[Evaluation]:
    return db.exec(select(Evaluation).where(Evaluation.application_id == app_id).order_by(Evaluation.id.desc())).first()


def _latest_decision(db: Session, app_id: int) -> Optional[Decision]:
    return db.exec(select(Decision).where(Decision.application_id == app_id).order_by(Decision.id.desc())).first()


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
    ev = _latest_eval(db, app.id)
    dec = _latest_decision(db, app.id)
    email = db.exec(select(Email).where(Email.application_id == app.id)).first()
    return {
        **_row(db, app),
        "job": {"id": job.id, "title": job.title} if job else None,
        "score": ({**s.criteria_json, "total": s.total, "model": s.model, "created_at": s.created_at.isoformat()} if s else None),
        "security": app.security_flags_json,
        "anonymized_cv": app.anonymized_profile_json.get("text", ""),
        "removed_personal_info": len(app.anonymized_profile_json.get("removed", [])),
        "evaluation": ({**ev.model_dump(), "created_at": ev.created_at.isoformat()} if ev else None),
        "final_decision": ({**dec.model_dump(), "created_at": dec.created_at.isoformat()} if dec else None),
        "email_id": email.id if email else None,
        "interview": _interview(db, app),
        "scheduling": scheduler.scheduling_status(db, app.id),
    }


def _interview(db: Session, app: Application) -> dict | None:
    """Questions (with rubric, for HR), invitation status, demo link, and answers if submitted."""
    if app.status in (ApplicationStatus.RECEIVED, ApplicationStatus.SCREENED, ApplicationStatus.SCORED,
                      ApplicationStatus.QUARANTINED):
        return None
    invite = db.exec(select(Draft).where(Draft.application_id == app.id, Draft.type == DraftType.INVITE)
                     .order_by(Draft.id.desc())).first()
    sub = db.exec(select(VideoSubmission).where(VideoSubmission.application_id == app.id)
                  .order_by(VideoSubmission.id.desc())).first()
    link = None
    if invite:
        m = re.search(r"https?://\S+/portal/\S+", invite.body)
        link = m.group(0) if m else None
    qs = questions_for(db, app) if (invite or sub) else []
    return {
        "questions": [{"id": q.id, "text": q.text, "rubric": q.rubric, "is_tailored": q.is_tailored} for q in qs],
        "invite_draft_id": invite.id if invite else None,
        "invite_status": invite.status.value if invite else None,
        "portal_link": link,
        "expires_at": sub.expires_at.isoformat() if sub else None,
        "answers": (sub.transcript_json.get("answers") if sub and sub.transcript_json else None),
        "answer_flags": (sub.transcript_json.get("injection_flags", []) if sub and sub.transcript_json else []),
        "submitted_at": (sub.transcript_json.get("submitted_at") if sub and sub.transcript_json else None),
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


@router.post("/{candidate_id}/invite")
def invite_candidate(candidate_id: int, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ HR asks for an interview invitation. The AI prepares questions + a draft; HR must still approve it."""
    app = db.get(Application, candidate_id)
    if not app:
        raise HTTPException(404, "Application not found")
    try:
        draft = prepare_invitation(db, app, actor=f"user:{user.id}")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"draft_id": draft.id, "status": draft.status.value,
            "message": "Invitation drafted. Review and approve it in Approvals - nothing has been sent."}


@router.post("/{candidate_id}/evaluate")
def evaluate(candidate_id: int, db: Session = Depends(get_session)):
    """(Re)evaluate the written answers -> recommendation (never a decision)."""
    app = db.get(Application, candidate_id)
    if not app:
        raise HTTPException(404, "Application not found")
    try:
        ev = evaluate_interview(db, app)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"recommendation": ev.recommendation, "confidence": ev.confidence, "status": app.status.value}


OUTCOME_EMAILS = {
    "advance": (
        "Good news about your application - {job}",
        "Hello {first},\n\nThank you for your answers to our written interview. We were impressed and would like "
        "to invite you to a final interview with our team. We will contact you shortly to agree on a time.\n\n"
        "Best regards,\nHR Team",
    ),
    "reject": (
        "Your application - {job}",
        "Hello {first},\n\nThank you for the time you spent on your application and on our written interview. "
        "After careful review, we have decided not to move forward with your application for this position.\n\n"
        "We wish you all the best in your search.\n\nBest regards,\nHR Team",
    ),
}


@router.post("/{candidate_id}/decision")
def make_decision(candidate_id: int, req: DecisionRequest, db: Session = Depends(get_session),
                  user: User = Depends(human)):
    """✋ HUMAN ONLY: final decision. If HR disagrees with the AI, a reason is required (accountability)."""
    app = db.get(Application, candidate_id)
    if not app:
        raise HTTPException(404, "Application not found")
    decision = req.decision.strip().lower()
    if decision not in OUTCOME_EMAILS:
        raise HTTPException(422, "Decision must be 'advance' or 'reject'.")
    ev = _latest_eval(db, app.id)
    ai = ev.recommendation if ev else "None"
    disagrees = (decision == "advance" and ai == "Not recommended") or (decision == "reject" and ai == "Advance")
    if len(req.note.strip()) < 10:
        if decision == "reject":
            raise HTTPException(422, "Please write a short reason for the rejection (10+ characters). "
                                     "It is saved in the audit log, so the decision can be explained later.")
        if disagrees:
            raise HTTPException(422, f"The AI recommended '{ai}'. Please write a short reason (10+ characters) "
                                     f"for advancing this candidate. It is saved in the audit log.")
    try:
        transition(db, app, ApplicationStatus.DECIDED, actor=f"user:{user.id}")
    except StateTransitionError as e:
        raise HTTPException(400, str(e))

    db.add(Decision(application_id=app.id, decision=decision, ai_recommendation=ai, agrees_with_ai=not disagrees,
                    note=req.note.strip()[:1000], decided_by=f"user:{user.id}"))
    cand = db.get(Candidate, app.candidate_id)
    job = db.get(Job, app.job_id)
    if decision == "advance":
        # propose 3 interview slots from HR's free time (held until the candidate answers)
        db.commit()
        _offer, draft = scheduler.create_offer(db, app, actor=f"user:{user.id}")
    else:
        subject, body = OUTCOME_EMAILS[decision]
        first = (cand.name or "").split(" ")[0] if cand else "there"
        draft = Draft(application_id=app.id, to_addr=cand.email if cand else "", type=DraftType.REJECTION,
                      subject=subject.format(job=job.title if job else ""), body=body.format(first=first))
        db.add(draft)
        db.commit()
        db.refresh(draft)
    log_audit(db, actor=f"user:{user.id}", action="final_decision", entity="application", entity_id=app.id,
              payload={"decision": decision, "ai": ai, "agrees_with_ai": not disagrees, "note": req.note[:200]})
    msg = ("Decision saved. 3 interview times were reserved in your calendar; the email proposing them is waiting "
           "in Approvals." if decision == "advance" else "Decision saved. The email to the candidate is waiting in Approvals.")
    return {"id": app.id, "status": app.status.value, "decision": decision, "agrees_with_ai": not disagrees,
            "draft_id": draft.id, "message": msg}


@router.post("/{candidate_id}/schedule/new")
def new_slots(candidate_id: int, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ Propose 3 new interview times (after the candidate declined, or the offer expired).
    Uses what the candidate wrote about their availability."""
    app = db.get(Application, candidate_id)
    dec = _latest_decision(db, candidate_id) if app else None
    if not app or not dec or dec.decision != "advance":
        raise HTTPException(400, "Only advanced candidates can be scheduled.")
    scheduler.expire_stale(db)
    st = scheduler.scheduling_status(db, app.id)
    if st and st["status"] in ("draft", "pending", "booked"):
        raise HTTPException(400, f"There is already an offer in status '{st['status']}'.")
    prefs = scheduler.parse_availability(st["availability_note"], __import__("datetime").datetime.now()) if st else None
    _offer, draft = scheduler.create_offer(db, app, actor=f"user:{user.id}", prefs=prefs,
                                           round_no=(st["round"] + 1) if st else 1)
    return {"draft_id": draft.id, "message": "3 new times reserved. The email is waiting in Approvals."}


@router.get("/{candidate_id}/interview.ics")
def interview_ics(candidate_id: int, db: Session = Depends(get_session)):
    """Calendar file for the booked interview (import into Google Calendar / Outlook)."""
    st = scheduler.scheduling_status(db, candidate_id)
    slot_info = next((s for s in (st or {}).get("slots", []) if s["status"] == "booked"), None)
    if not slot_info:
        raise HTTPException(404, "No booked interview.")
    from ..models import InterviewSlot
    slot = db.get(InterviewSlot, slot_info["id"])
    app = db.get(Application, candidate_id)
    job = db.get(Job, app.job_id)
    body = scheduler.ics_for(slot, f"Final interview - Candidate #{app.id:03d} - {job.title}")
    return Response(body, media_type="text/calendar",
                    headers={"Content-Disposition": f'attachment; filename="interview-{app.id:03d}.ics"'})
