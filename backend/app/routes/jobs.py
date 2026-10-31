"""Job posting routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..audit import log_audit
from ..auth import require_role
from ..db import get_session
from ..models import Application, ApplicationStatus, Job, User, UserRole
from ..schemas import JobCreate, RubricApprove
from ..services.rubric import GENERIC_RUBRIC, normalize_rubric
from ..services.scorer import score_application

router = APIRouter(prefix="/jobs", tags=["jobs"])
human = require_role(UserRole.RECRUITER, UserRole.ADMIN)


def _job_out(job: Job, db: Session) -> dict:
    apps = db.exec(select(Application).where(Application.job_id == job.id)).all()
    counts: dict[str, int] = {}
    for a in apps:
        counts[a.status.value] = counts.get(a.status.value, 0) + 1
    return {
        "id": job.id, "title": job.title, "description": job.description,
        "rubric": normalize_rubric(job.rubric_json), "rubric_approved_by": job.rubric_approved_by,
        "created_at": job.created_at.isoformat(), "applications": len(apps), "status_counts": counts,
        "quarantined": counts.get("QUARANTINED", 0),
    }


@router.get("")
@router.get("/")
def list_jobs(db: Session = Depends(get_session)):
    return [_job_out(j, db) for j in db.exec(select(Job)).all()]


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_session)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return _job_out(job, db)


@router.post("")
@router.post("/")
def create_job(req: JobCreate, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ Create a job with a generic rubric (HR can then edit and approve it)."""
    job = Job(title=req.title, description=req.description, rubric_json=GENERIC_RUBRIC)
    db.add(job)
    db.commit()
    db.refresh(job)
    log_audit(db, actor=f"user:{user.id}", action="create_job", entity="job", entity_id=job.id)
    return _job_out(job, db)


@router.post("/{job_id}/rubric/approve")
def approve_rubric(job_id: int, req: RubricApprove, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ HR approves (and optionally edits) the scoring rubric."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    crit = normalize_rubric(req.rubric_json) if req.rubric_json else normalize_rubric(job.rubric_json)
    job.rubric_json = {"criteria": crit}
    job.rubric_approved_by = user.id
    db.add(job)
    db.commit()
    log_audit(db, actor=f"user:{user.id}", action="approve_rubric", entity="job", entity_id=job.id)
    return _job_out(job, db)


@router.post("/{job_id}/score_all")
def score_all(job_id: int, db: Session = Depends(get_session)):
    """Score every screened (not quarantined) application that has no score yet."""
    apps = db.exec(select(Application).where(Application.job_id == job_id,
                                             Application.status == ApplicationStatus.SCREENED)).all()
    done, errors = 0, []
    for a in apps:
        try:
            score_application(db, a)
            done += 1
        except Exception as e:  # keep going
            errors.append(f"application {a.id}: {e}")
    return {"scored": done, "errors": errors}
