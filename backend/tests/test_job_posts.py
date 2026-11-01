"""Job posts: exact facts and contact written by code, AI numbers fact-checked, fairness check,
unfair points never used for scoring, human-only publication, public page, application routing."""
from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from app.db import engine
from app.main import app
from app.models import Application, Email
from app.schemas import JobPostDraft
from app.services import job_posts as JP
from app.services.triage import _create_application
from tests.conftest import logged_in_client

DETAILS = {
    "title": "Data Analyst", "team": "Finance", "location": "Sfax", "work_mode": "onsite",
    "contract_type": "fixed_term", "contract_length": "6 months", "salary_min": 2000, "salary_max": 2600,
    "currency": "TND", "must_haves": "SQL\nExcel or Google Sheets\nNative English speaker",
    "nice_to_haves": "Power BI", "tasks": "Build monthly reports", "benefits": "Health insurance",
}


def _gen(c, details=None):
    settings.llm_api_key = ""
    r = c.post("/jobs/posts/generate", json={"details": details or DETAILS})
    assert r.status_code == 200, r.text
    return r.json()


def test_facts_and_contact_are_exact():
    p = _gen(logged_in_client())
    assert "Fixed-term contract, 6 months" in p["text"]
    assert "2,000 - 2,600 TND" in p["text"]
    assert settings.hr_contact_email in p["text"] and p["code"] in p["text"]
    assert p["checks"]["contact_ok"] and p["checks"]["facts_ok"]


def test_required_fields():
    c = logged_in_client()
    assert c.post("/jobs/posts/generate", json={"details": {"title": "X"}}).status_code == 422  # no must-have
    bad = {**DETAILS, "contract_length": ""}
    assert c.post("/jobs/posts/generate", json={"details": bad}).status_code == 422          # fixed-term needs a length


def test_ai_numbers_not_given_by_hr_are_removed():
    d = JP.clean_details(DETAILS)
    draft = JobPostDraft(intro="Join a team of 40 people. You will grow fast.", responsibilities=["Build reports"],
                         requirements=["SQL", "Excel", "5 years of Python"], nice_to_have=[], offer=["Bonus of 3000 TND"])
    fixed, removed = JP._fact_check(draft, d)
    assert "40 people" not in fixed.intro and "grow fast" in fixed.intro
    assert all("3000" not in x for x in fixed.offer)
    assert len(removed) == 3


def test_fairness_flags_and_unfair_points_never_score():
    p = _gen(logged_in_client(), {**DETAILS, "must_haves": "SQL\nYoung and dynamic\nNative English speaker"})
    phrases = {f["phrase"].lower() for f in p["checks"]["fairness"]}
    assert "young" in phrases and any("native" in x for x in phrases)
    labels = [r["label"] for r in p["rubric"]]
    assert "SQL" in labels and not any("Young" in x or "Native" in x for x in labels)
    for text in ("We want a rockstar salesman", "Applicants must be 25-35 years old", "He will report to the CEO"):
        assert JP.fairness_issues(text), text
    assert not JP.fairness_issues("You will report to the head of finance. Fluent in English.")


def test_publish_is_human_and_guarded():
    c = logged_in_client()
    p = _gen(c)
    jid = p["job_id"]
    anon = TestClient(app)
    assert anon.post(f"/jobs/{jid}/post/publish", json={}).status_code == 401
    r = c.post(f"/jobs/{jid}/post/publish", json={})
    assert r.status_code == 422  # "native speaker" still in the text
    # removing the contact line is refused
    c.put(f"/jobs/{jid}/post", json={"text": p["text"].replace(settings.hr_contact_email, "someone@else.test")})
    assert c.post(f"/jobs/{jid}/post/publish", json={"note": "checked with legal team"}).status_code == 422
    # fixed text publishes; public page works without login; drafts are never public
    c.put(f"/jobs/{jid}/post", json={"text": p["text"].replace("Native English speaker", "Fluent in English")})
    r = c.post(f"/jobs/{jid}/post/publish", json={})
    assert r.status_code == 200 and r.json()["status"] == "published"
    slug = r.json()["public_slug"]
    assert anon.get(f"/careers/{slug}").status_code == 200
    draft = _gen(c)
    assert anon.get(f"/careers/{draft['code'].lower()}").status_code == 404
    # published posts cannot be edited silently
    assert c.put(f"/jobs/{jid}/post", json={"text": "changed"}).status_code == 422


def test_applications_are_routed_by_job_code():
    c = logged_in_client()
    p = _gen(c, {**DETAILS, "must_haves": "SQL"})
    c.post(f"/jobs/{p['job_id']}/post/publish", json={})
    with Session(engine) as db:
        raw = {"from_name": "Ana Lyst", "from_addr": f"ana-{datetime.now().timestamp()}@mail.test",
               "subject": f"Application {p['code']} - Data Analyst", "body": "Please find my CV attached."}
        app_row = _create_application(db, raw, {"filename": "cv.pdf", "path": "/nonexistent.pdf", "safe": True,
                                                "flags": [], "hidden_text": []})
        assert app_row.job_id == p["job_id"]


def test_demo_applications_go_through_the_pipeline():
    c = logged_in_client()
    p = _gen(c, {**DETAILS, "must_haves": "SQL\nExcel\nYoung and dynamic"})
    jid = p["job_id"]
    assert c.post(f"/jobs/{jid}/post/demo_applications").status_code == 400  # not published yet
    c.post(f"/jobs/{jid}/post/publish", json={"note": "demo test, wording checked"})
    r = c.post(f"/jobs/{jid}/post/demo_applications")
    assert r.status_code == 200 and len(r.json()["applications"]) == 4
    rows = c.get(f"/candidates?job_id={jid}").json()
    assert len(rows) == 4 and all(x["status"] == "SCORED" for x in rows)
    scores = {a["level"]: next(x["total"] for x in rows if x["id"] == a["application_id"]) for a in r.json()["applications"]}
    assert scores["strong"] > scores["medium"] > scores["weak"]
    old = settings.app_env
    settings.app_env = "prod"
    try:
        assert c.post(f"/jobs/{jid}/post/demo_applications").status_code == 403
    finally:
        settings.app_env = old
