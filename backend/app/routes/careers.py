"""Public careers page: only PUBLISHED job posts, by their unguessable link. No login."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Job, JobPost

router = APIRouter(prefix="/careers", tags=["careers (public)"])


@router.get("/{slug}")
def public_post(slug: str, db: Session = Depends(get_session)):
    if not slug or len(slug) > 80:
        raise HTTPException(404, "Not found")
    post = db.exec(select(JobPost).where(JobPost.public_slug == slug, JobPost.status == "published")).first()
    if not post:
        raise HTTPException(404, "This job post is not available.")
    job = db.get(Job, post.job_id)
    return {"title": job.title, "code": post.code, "text": post.text,
            "published_at": post.published_at.isoformat() if post.published_at else None}
