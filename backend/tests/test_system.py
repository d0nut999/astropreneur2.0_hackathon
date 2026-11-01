"""Demo tools: reset and status."""
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import logged_in_client


def test_reset_requires_login():
    assert TestClient(app).post("/system/reset_demo").status_code == 401


def test_reset_restores_demo_and_keeps_audit_log():
    c = logged_in_client()
    c.post("/emails/load_demo")
    from sqlmodel import Session, select
    from app.db import engine
    from app.models import AuditLog
    with Session(engine) as db:
        oldest = db.exec(select(AuditLog).order_by(AuditLog.id)).first().id
        count_before = len(db.exec(select(AuditLog)).all())
    r = c.post("/system/reset_demo").json()
    assert r["ok"] and r["imported"] == 21
    assert c.get("/system/status").json()["counts"]["emails"] == 21
    with Session(engine) as db:  # append-only: nothing deleted, new entries added
        assert db.exec(select(AuditLog).order_by(AuditLog.id)).first().id == oldest
        assert len(db.exec(select(AuditLog)).all()) > count_before
