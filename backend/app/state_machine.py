"""Application state machine."""
from enum import Enum
from .models import ApplicationStatus, Application, AuditLog
from sqlmodel import Session
from datetime import datetime
import hashlib
import json


class StateTransitionError(Exception):
    """Invalid state transition."""
    pass


# Valid transitions: from_state -> list of allowed to_states
TRANSITIONS = {
    ApplicationStatus.RECEIVED: [ApplicationStatus.SCREENED, ApplicationStatus.QUARANTINED],
    ApplicationStatus.QUARANTINED: [],  # Dead end until human intervention
    ApplicationStatus.SCREENED: [ApplicationStatus.SCORED],
    ApplicationStatus.SCORED: [ApplicationStatus.SHORTLISTED],
    ApplicationStatus.SHORTLISTED: [ApplicationStatus.INVITED],
    ApplicationStatus.INVITED: [ApplicationStatus.VIDEO_SUBMITTED],
    ApplicationStatus.VIDEO_SUBMITTED: [ApplicationStatus.EVALUATED],
    ApplicationStatus.EVALUATED: [ApplicationStatus.DECIDED],
    ApplicationStatus.DECIDED: [],
}

# States that ONLY humans may enter
HUMAN_ONLY_STATES = {
    ApplicationStatus.SHORTLISTED,
    ApplicationStatus.INVITED,
    ApplicationStatus.DECIDED,
}


def transition(
    db: Session,
    application: Application,
    to_state: ApplicationStatus,
    actor: str,
) -> Application:
    """
    Transition an application to a new state.

    Args:
        db: Database session
        application: Application to transition
        to_state: Target state
        actor: Who is making the change ("ai", "system", or "user:<id>")

    Raises:
        StateTransitionError: If transition is invalid or actor lacks permission

    Returns:
        Updated application
    """
    from_state = application.status

    # Check if transition is valid
    if to_state not in TRANSITIONS.get(from_state, []):
        raise StateTransitionError(
            f"Cannot transition from {from_state} to {to_state}"
        )

    # Check if actor is human for human-only states
    if to_state in HUMAN_ONLY_STATES and actor.startswith("ai"):
        raise StateTransitionError(
            f"Only humans may transition to {to_state}"
        )

    # Update status
    application.status = to_state

    # Create audit entry
    payload = {
        "from_state": from_state.value,
        "to_state": to_state.value,
    }
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    audit = AuditLog(
        actor=actor,
        action="transition",
        entity="application",
        entity_id=application.id,
        payload_hash=payload_hash,
    )

    db.add(audit)
    db.add(application)
    db.commit()
    db.refresh(application)

    return application
