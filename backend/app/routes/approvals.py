"""Approval queue routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from ..db import get_session
from ..schemas import DraftResponse

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/")
async def list_pending_approvals(db: Session = Depends(get_session)):
    """List pending draft approvals."""
    # TODO: Query Draft table where status = PENDING
    return [
        {
            "id": 1,
            "application_id": 1,
            "type": "invite",
            "subject": "You're invited to interview",
            "body": "Dear John...",
            "status": "pending",
            "approved_by": None,
            "created_at": "2024-01-15T10:00:00",
        }
    ]


@router.post("/{draft_id}/approve")
async def approve_draft(draft_id: int, db: Session = Depends(get_session)):
    """Approve a draft (human only)."""
    # TODO: Update draft status, queue for sending
    return {"message": "Draft approved"}


@router.post("/{draft_id}/reject")
async def reject_draft(draft_id: int, db: Session = Depends(get_session)):
    """Reject a draft."""
    # TODO: Update draft status to REJECTED
    return {"message": "Draft rejected"}
