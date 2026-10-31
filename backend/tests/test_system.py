"""Demo tools: reset and status."""
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import logged_in_client


def test_reset_requires_login():
    assert TestClient(app).post("/system/reset_demo").status_code == 401


def test_reset_restores_demo_and_keeps_audit_log():
    c = logged_in_client()
    c.post("/emails/load_demo")
    audit_before = len(c.get("/audit?limit=1000").json())
    r = c.post("/system/reset_demo").json()
    assert r["ok"] and r["imported"] == 15
    assert c.get("/system/status").json()["counts"]["emails"] == 15
    assert len(c.get("/audit?limit=1000").json()) > audit_before  # append-only: nothing deleted
