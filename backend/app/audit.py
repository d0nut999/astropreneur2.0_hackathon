"""Audit logging helper."""
import hashlib
import json
from sqlmodel import Session
from .models import AuditLog


def log_audit(
    db: Session,
    actor: str,
    action: str,
    entity: str,
    entity_id: int,
    payload: dict = None,
):
    """Create an audit log entry (append-only)."""
    payload_hash = hashlib.sha256(
        json.dumps(payload or {}, sort_keys=True).encode()
    ).hexdigest()

    audit = AuditLog(
        actor=actor,
        action=action,
        entity=entity,
        entity_id=entity_id,
        payload_hash=payload_hash,
    )
    db.add(audit)
    db.commit()
