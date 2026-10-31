"""Audit log routes."""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from ..db import get_session
from ..models import AuditLog
from ..schemas import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/")
async def list_audit_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    """List audit logs (append-only)."""
    logs = db.exec(select(AuditLog).offset(skip).limit(limit)).all()
    return [AuditLogResponse.model_validate(log) for log in logs]
