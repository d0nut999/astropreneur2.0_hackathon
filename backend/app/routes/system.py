"""System tools for the HR team: status, AI connection test, demo reset."""
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from sqlmodel import Session, select

from ..audit import log_audit
from ..auth import require_role
from ..config import settings
from ..db import get_session
from ..models import (
    Application, Candidate, Decision, Draft, Email, Evaluation, Event, InterviewQuestion, InterviewSlot, Score,
    ScheduleOffer, SentEmail, TimeRequest, User, UserRole, VideoSubmission,
)
from ..services.inbox import load_demo_emails
from ..services.triage import process_incoming

router = APIRouter(prefix="/system", tags=["system"])
human = require_role(UserRole.RECRUITER, UserRole.ADMIN)
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@router.get("/status")
def status(db: Session = Depends(get_session)):
    """What mode is HireGuard running in?"""
    return {
        "ai_configured": bool(settings.llm_api_key),
        "ai_model": settings.llm_model if settings.llm_api_key else None,
        "ai_provider": settings.llm_base_url.split("//")[-1].split("/")[0],
        "mode": "ai" if settings.llm_api_key else "offline-rules",
        "env": settings.app_env,
        "counts": {
            "emails": len(db.exec(select(Email)).all()),
            "applications": len(db.exec(select(Application)).all()),
            "pending_drafts": len(db.exec(select(Draft).where(Draft.status == "pending")).all()),
        },
    }


@router.post("/test_ai")
def test_ai(user: User = Depends(human)):
    """Send one tiny request to the AI provider to check the key and model work."""
    if not settings.llm_api_key:
        return {"ok": False, "message": "No LLM_API_KEY in backend/.env - HireGuard runs on offline rules."}
    started = time.time()
    try:
        client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url, timeout=20)
        r = client.chat.completions.create(
            model=settings.llm_model, temperature=0, max_tokens=20,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
        reply = (r.choices[0].message.content or "").strip()[:40]
        return {"ok": True, "model": settings.llm_model, "seconds": round(time.time() - started, 1), "reply": reply,
                "message": f"AI connected ({settings.llm_model}, {time.time() - started:.1f}s)"}
    except Exception as e:
        msg = str(e)
        if settings.llm_api_key in msg:
            msg = msg.replace(settings.llm_api_key, "***")  # never echo the key
        return {"ok": False, "model": settings.llm_model, "message": f"AI call failed: {msg[:300]}"}


@router.post("/reset_demo")
def reset_demo(reload: bool = True, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ Dev only: remove all emails, candidates, scores, interviews, decisions and drafts, then reload
    the demo emails. Users, jobs and the audit log are kept (the audit log is append-only)."""
    if settings.app_env != "dev":
        raise HTTPException(403, "Demo reset is only available in dev mode.")
    from ..services.followups import set_demo_shift
    from ..services.employees import seed_employees
    set_demo_shift(0)
    seed_employees(db)  # fictional staff + leave history (also removes leave requests linked to emails)
    for model in (SentEmail, TimeRequest, InterviewSlot, ScheduleOffer, Decision, Evaluation, VideoSubmission, Draft, Event, Score, Email):
        for row in db.exec(select(model)).all():
            db.delete(row)
    db.commit()
    for q in db.exec(select(InterviewQuestion).where(InterviewQuestion.application_id != None)).all():  # noqa: E711
        db.delete(q)
    db.commit()
    for model in (Application, Candidate):
        for row in db.exec(select(model)).all():
            db.delete(row)
    db.commit()
    # job posts created during the demo are removed (the seeded job stays)
    from ..models import Job, JobPost
    for post in db.exec(select(JobPost)).all():
        job = db.get(Job, post.job_id)
        for q in db.exec(select(InterviewQuestion).where(InterviewQuestion.job_id == post.job_id)).all():
            db.delete(q)
        db.delete(post)
        db.commit()
        if job:
            db.delete(job)
    db.commit()
    for folder in ("uploads", "outbox"):
        shutil.rmtree(DATA_DIR / folder, ignore_errors=True)
    log_audit(db, actor=f"user:{user.id}", action="reset_demo", entity="system", entity_id=0)

    imported = 0
    if reload:
        for raw in load_demo_emails():
            if process_incoming(db, raw):
                imported += 1
    return {"ok": True, "imported": imported,
            "message": f"Demo reset. {imported} demo emails loaded." if reload else "Demo reset."}
