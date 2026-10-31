"""Shared test helpers."""
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth import hash_password
from app.db import engine, init_db
from app.main import app
from app.models import User, UserRole

TEST_EMAIL = "tester@fictional-company.test"
TEST_PASSWORD = "tester-password-123"


def ensure_test_user():
    init_db()
    with Session(engine) as db:
        if not db.exec(select(User).where(User.email == TEST_EMAIL)).first():
            db.add(User(email=TEST_EMAIL, password_hash=hash_password(TEST_PASSWORD), role=UserRole.RECRUITER))
            db.commit()


def logged_in_client() -> TestClient:
    """A TestClient with a session cookie and the CSRF header set, like the real frontend."""
    ensure_test_user()
    c = TestClient(app)
    r = c.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return c
