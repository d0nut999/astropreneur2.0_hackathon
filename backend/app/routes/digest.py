"""Daily digest route."""
from fastapi import APIRouter, Depends
from sqlmodel import Session
from ..db import get_session
from ..services.digest import generate_digest

router = APIRouter(prefix="/digest", tags=["digest"])


@router.get("/today")
async def get_digest_today(db: Session = Depends(get_session)):
    """Get today's digest (high-urgency emails, pending approvals)."""
    return generate_digest()
