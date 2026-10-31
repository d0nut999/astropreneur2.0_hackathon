"""Interview flow: human-only invite, link locked until approval, one-time use, no rubric leak."""
import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient  # noqa: F401

from tests.conftest import logged_in_client
from sqlmodel import Session, select

from app.auth import hash_password
from app.db import engine, init_db
from app.main import app
from app.models import Application, ApplicationStatus, Candidate, Job, User, UserRole, VideoSubmission
from app.services.interview import hash_token


def _setup():
    init_db()
    with Session(engine) as db:
        if not db.exec(select(User)).first():
            db.add(User(email="hr@test.test", password_hash=hash_password("x"), role=UserRole.RECRUITER))
        job = Job(title="Test job", description="Python")
        db.add(job)
        db.commit()
        cand = Candidate(name="Test Person", email=f"t-{uuid.uuid4().hex[:8]}@example.com")
        db.add(cand)
        db.commit()
        a = Application(job_id=job.id, candidate_id=cand.id, status=ApplicationStatus.SCORED)
        db.add(a)
        db.commit()
        return a.id


def test_full_invitation_flow():
    app_id = _setup()
    c = logged_in_client()
    assert c.post(f"/candidates/{app_id}/invite").status_code == 400  # not shortlisted yet
    assert c.post(f"/candidates/{app_id}/shortlist").status_code == 200

    draft_id = c.post(f"/candidates/{app_id}/invite").json()["draft_id"]
    link = c.get(f"/candidates/{app_id}").json()["interview"]["portal_link"]
    token = link.rsplit("/", 1)[1]

    # Locked until HR approves the invitation
    assert c.get(f"/portal/{token}").status_code == 403
    assert c.post(f"/approvals/{draft_id}/approve").json()["sent"]

    session = c.get(f"/portal/{token}").json()
    assert len(session["questions"]) == 3
    assert all("rubric" not in q for q in session["questions"])  # candidate never sees the rubric

    answers = {str(q["id"]): "A concrete answer." for q in session["questions"]}
    assert c.post(f"/portal/{token}/answers", json={"answers": answers}).status_code == 200
    assert c.get(f"/portal/{token}").status_code == 410  # one-time link
    assert c.get(f"/candidates/{app_id}").json()["status"] == "EVALUATED"  # answers evaluated right away


def test_raw_token_is_never_stored_and_expired_links_fail():
    app_id = _setup()
    c = logged_in_client()
    c.post(f"/candidates/{app_id}/shortlist")
    draft_id = c.post(f"/candidates/{app_id}/invite").json()["draft_id"]
    token = c.get(f"/candidates/{app_id}").json()["interview"]["portal_link"].rsplit("/", 1)[1]
    c.post(f"/approvals/{draft_id}/approve")
    with Session(engine) as db:
        sub = db.exec(select(VideoSubmission).where(VideoSubmission.application_id == app_id)).first()
        assert sub.token_hash == hash_token(token) and token not in sub.token_hash
        sub.expires_at = datetime.now() - timedelta(minutes=1)
        db.add(sub)
        db.commit()
    assert c.get(f"/portal/{token}").status_code == 410
