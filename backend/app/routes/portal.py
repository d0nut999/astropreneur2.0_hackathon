"""Candidate portal routes (public, token-protected)."""
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlmodel import Session
from ..db import get_session

router = APIRouter(prefix="/portal", tags=["portal"])


@router.get("/{token}")
async def get_portal_session(token: str, db: Session = Depends(get_session)):
    """Get portal session for candidate (one-time token)."""
    # TODO: Verify token, get application, return questions
    return {
        "application_id": 1,
        "questions": [
            {"id": 1, "text": "Tell us about your experience", "rubric": "..."}
        ],
        "token_remaining_hours": 24,
    }


@router.post("/{token}/video")
async def upload_video(token: str, file: UploadFile = File(...), db: Session = Depends(get_session)):
    """Upload video or audio response (or text fallback)."""
    # TODO: Verify token, save file, mark submission as received
    return {"success": True, "message": "Video uploaded"}
