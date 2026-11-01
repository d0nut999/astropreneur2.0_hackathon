"""Job posting routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..audit import log_audit
from ..auth import require_role
from ..db import get_session
from pydantic import BaseModel

from ..models import Application, ApplicationStatus, Job, JobPost, User, UserRole
from ..services import job_posts as JP
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
        "post": (lambda p: {"code": p.code, "status": p.status, "public_slug": p.public_slug if p.status == "published" else ""}
                 if p else None)(db.exec(select(JobPost).where(JobPost.job_id == job.id)).first()),
    }


@router.get("")
@router.get("/")
def list_jobs(db: Session = Depends(get_session)):
    return [_job_out(j, db) for j in db.exec(select(Job)).all()]


class PostDetails(BaseModel):
    details: dict


class PostText(BaseModel):
    text: str


class PublishReq(BaseModel):
    note: str = ""


def _post(job_id: int, db: Session) -> JobPost:
    post = db.exec(select(JobPost).where(JobPost.job_id == job_id)).first()
    if not post:
        raise HTTPException(404, "Job post not found")
    return post


@router.post("/posts/generate")
def generate_post(req: PostDetails, db: Session = Depends(get_session), user: User = Depends(human)):
    """HR's key facts -> AI draft (+ fact check, fairness check, scoring criteria). Nothing is published."""
    try:
        post = JP.generate(db, req.details, user.id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return JP.post_json(db, post)


@router.get("/{job_id}/post")
def get_post(job_id: int, db: Session = Depends(get_session)):
    return JP.post_json(db, _post(job_id, db))


@router.post("/{job_id}/post/generate")
def regenerate_post(job_id: int, req: PostDetails, db: Session = Depends(get_session), user: User = Depends(human)):
    try:
        post = JP.generate(db, req.details, user.id, job_id=job_id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return JP.post_json(db, post)


@router.put("/{job_id}/post")
def edit_post(job_id: int, req: PostText, db: Session = Depends(get_session), user: User = Depends(human)):
    try:
        post = JP.update_text(db, _post(job_id, db), req.text, user.id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return JP.post_json(db, post)


@router.post("/{job_id}/post/publish")
def publish_post(job_id: int, req: PublishReq, db: Session = Depends(get_session), user: User = Depends(human)):
    """✋ HUMAN ONLY: publish the post (also approves the scoring criteria shown next to it)."""
    try:
        post = JP.publish(db, _post(job_id, db), user.id, req.note)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return JP.post_json(db, post)


@router.post("/{job_id}/post/demo_applications")
def demo_applications(job_id: int, db: Session = Depends(get_session), user: User = Depends(human)):
    """Dev only: 4 fictional candidates (strong -> weak) apply by email with this job's code."""
    from ..config import settings
    if settings.app_env != "dev":
        raise HTTPException(403, "Demo applications are only available in dev mode.")
    post = _post(job_id, db)
    if post.status != "published":
        raise HTTPException(400, "Publish the job post first: candidates can only apply to a published job.")
    made = JP.demo_applications(db, post)
    return {"applications": made, "message": f"{len(made)} applications received by email and scored for {post.code}."}


@router.post("/{job_id}/post/close")
def close_post(job_id: int, db: Session = Depends(get_session), user: User = Depends(human)):
    return JP.post_json(db, JP.close(db, _post(job_id, db), user.id))


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
