"""Bulk shortlist + personal invitations + approve selected."""
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import logged_in_client


def test_bulk_requires_login():
    c = TestClient(app)
    assert c.post("/candidates/bulk/shortlist_and_invite", json={"ids": [1]}).status_code == 401
    assert c.post("/approvals/bulk_approve", json={"ids": [1]}).status_code == 401


def test_bulk_shortlist_creates_one_personal_invitation_each_and_approve_selected():
    c = logged_in_client()
    c.post("/system/reset_demo")
    rows = c.get("/candidates?job_id=1").json()
    scored = [r["id"] for r in rows if r["status"] == "SCORED"]
    blocked = [r["id"] for r in rows if r["status"] == "QUARANTINED"]
    assert len(scored) >= 2 and blocked

    r = c.post("/candidates/bulk/shortlist_and_invite", json={"ids": scored + blocked[:1]}).json()
    assert r["invitations"] == len(scored)
    assert any(not x["ok"] for x in r["results"])           # quarantined CV is refused, not invited

    drafts = [d for d in c.get("/approvals").json() if d["type"] == "invite"]
    assert len(drafts) == len(scored)
    assert len({d["to_addr"] for d in drafts}) == len(scored)  # one per candidate, to their own address
    assert len({d["body"] for d in drafts}) == len(scored)     # personal: tailored question + own link

    chosen = [drafts[0]["id"]]
    res = c.post("/approvals/bulk_approve", json={"ids": chosen}).json()
    assert res["sent"] == 1
    statuses = {r["id"]: r["status"] for r in c.get("/candidates?job_id=1").json()}
    assert sum(1 for i in scored if statuses[i] == "INVITED") == 1   # only the approved one is invited
    assert sum(1 for i in scored if statuses[i] == "SHORTLISTED") == len(scored) - 1
