"""Candidate and application routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from ..db import get_session
from ..schemas import CandidateDetailResponse, ShortlistRequest, DecisionRequest

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("/")
async def list_candidates(job_id: int, db: Session = Depends(get_session)):
    """List candidates for a job (ranked by score, mock data)."""
    # TODO: Query applications for job, join scores, rank
    return []


@router.get("/{candidate_id}")
async def get_candidate_detail(candidate_id: int, db: Session = Depends(get_session)):
    """Get full candidate profile (scores, evidence, flags, evaluation)."""
    # TODO: Query candidate + application + scores + evaluation
    return {
        "candidate": {"id": 1, "name": "John Doe", "email": "john@example.com"},
        "application": {
            "id": 1,
            "job_id": 1,
            "candidate_id": 1,
            "status": "SCREENED",
            "security_flags_json": {},
            "anonymized_profile_json": {},
            "created_at": "2024-01-15T10:00:00",
        },
        "scores": [],
        "evaluation": None,
    }


@router.post("/{candidate_id}/shortlist")
async def shortlist_candidate(candidate_id: int, req: ShortlistRequest, db: Session = Depends(get_session)):
    """Shortlist candidate (human only)."""
    # TODO: Update status to SHORTLISTED via state_machine
    return {"message": "Candidate shortlisted"}


@router.post("/{candidate_id}/decision")
async def make_decision(candidate_id: int, req: DecisionRequest, db: Session = Depends(get_session)):
    """Record final decision (human only)."""
    # TODO: Update status to DECIDED via state_machine
    return {"message": "Decision recorded"}
