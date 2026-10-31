"""Audit log routes."""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
@router.get("/")
async def list_audit_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    """List audit logs (append-only), newest first."""
    logs = db.exec(select(AuditLog).order_by(AuditLog.id.desc()).offset(skip).limit(limit)).all()
    return [log.model_dump() for log in logs]
