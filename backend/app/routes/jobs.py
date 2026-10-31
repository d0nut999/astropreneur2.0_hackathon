"""Job posting routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from ..db import get_session
from ..models import Job
from ..schemas import JobCreate, JobResponse, RubricApprove

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/")
async def list_jobs(db: Session = Depends(get_session)):
    """List all jobs (mock data)."""
    # TODO: Query real jobs
    return [
        {
            "id": 1,
            "title": "Senior Backend Engineer",
            "description": "We are hiring...",
            "rubric_json": {
                "experience": {"weight": 0.3},
                "technical_skills": {"weight": 0.5},
            },
            "rubric_approved_by": 1,
            "created_at": "2024-01-15T10:00:00",
        }
    ]


@router.post("/")
async def create_job(job: JobCreate, db: Session = Depends(get_session)):
    """Create a new job posting."""
    # TODO: Implement
    return {"id": 1, **job.model_dump(), "created_at": "2024-01-15T10:00:00"}


@router.post("/{job_id}/rubric/approve")
async def approve_rubric(job_id: int, req: RubricApprove, db: Session = Depends(get_session)):
    """Approve job rubric (human only)."""
    # TODO: Update job, set rubric_approved_by
    return {"message": "Rubric approved"}
