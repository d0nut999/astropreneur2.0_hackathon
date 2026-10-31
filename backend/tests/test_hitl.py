"""Test human-in-the-loop state machine rules."""
import uuid

import pytest
from sqlmodel import Session
from app.db import engine, init_db
from app.models import Application, ApplicationStatus, Job, Candidate
from app.state_machine import transition, StateTransitionError
from sqlmodel import Session


def setup_function():
    """Setup for each test."""
    init_db()


def test_ai_cannot_enter_shortlisted():
    """Verify AI actor cannot transition to SHORTLISTED."""
    with Session(engine) as db:
        # Create job and candidate
        job = Job(title="Test", description="Test", rubric_json={})
        db.add(job)
        db.commit()

        candidate = Candidate(name="Test", email=f"test-{uuid.uuid4().hex[:8]}@example.com")
        db.add(candidate)
        db.commit()

        # Create application at SCORED state
        app = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status=ApplicationStatus.SCORED,
        )
        db.add(app)
        db.commit()

        # Try to transition AI actor to SHORTLISTED (should fail)
        with pytest.raises(StateTransitionError, match="Only humans may"):
            transition(db, app, ApplicationStatus.SHORTLISTED, actor="ai")


def test_ai_cannot_enter_invited():
    """Verify AI actor cannot transition to INVITED."""
    with Session(engine) as db:
        job = Job(title="Test", description="Test", rubric_json={})
        db.add(job)
        db.commit()

        candidate = Candidate(name="Test", email=f"test-{uuid.uuid4().hex[:8]}@example.com")
        db.add(candidate)
        db.commit()

        app = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status=ApplicationStatus.SHORTLISTED,
        )
        db.add(app)
        db.commit()

        with pytest.raises(StateTransitionError, match="Only humans may"):
            transition(db, app, ApplicationStatus.INVITED, actor="ai")


def test_ai_cannot_enter_decided():
    """Verify AI actor cannot transition to DECIDED."""
    with Session(engine) as db:
        job = Job(title="Test", description="Test", rubric_json={})
        db.add(job)
        db.commit()

        candidate = Candidate(name="Test", email=f"test-{uuid.uuid4().hex[:8]}@example.com")
        db.add(candidate)
        db.commit()

        app = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status=ApplicationStatus.EVALUATED,
        )
        db.add(app)
        db.commit()

        with pytest.raises(StateTransitionError, match="Only humans may"):
            transition(db, app, ApplicationStatus.DECIDED, actor="ai")


def test_human_can_enter_shortlisted():
    """Verify human actor CAN transition to SHORTLISTED."""
    with Session(engine) as db:
        job = Job(title="Test", description="Test", rubric_json={})
        db.add(job)
        db.commit()

        candidate = Candidate(name="Test", email=f"test-{uuid.uuid4().hex[:8]}@example.com")
        db.add(candidate)
        db.commit()

        app = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status=ApplicationStatus.SCORED,
        )
        db.add(app)
        db.commit()

        # Human should succeed
        result = transition(db, app, ApplicationStatus.SHORTLISTED, actor="user:123")
        assert result.status == ApplicationStatus.SHORTLISTED
