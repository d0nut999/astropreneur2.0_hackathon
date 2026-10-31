"""Follow-ups: reminders become due after silence, carry a new link that only works once sent,
stop after the maximum, and HR can close the application. Nothing is sent without approval."""
import uuid

from sqlmodel import Session, select

from app.config import settings
from app.db import engine, init_db
from app.models import (
    Application, ApplicationStatus, Candidate, Decision, Draft, DraftStatus, DraftType, Job, ScheduleOffer, SentEmail,
)
from app.services import followups as fu
from tests.conftest import logged_in_client


def _app(status: ApplicationStatus, advanced: bool = False) -> int:
    init_db()
    with Session(engine) as db:
        job = Job(title="Follow-up job", description="Python")
        db.add(job)
        db.commit()
        cand = Candidate(name="Fola Upson", email=f"f-{uuid.uuid4().hex[:8]}@example.com")
        db.add(cand)
        db.commit()
        a = Application(job_id=job.id, candidate_id=cand.id, status=status)
        db.add(a)
        db.commit()
        if advanced:
            db.add(Decision(application_id=a.id, decision="advance", ai_recommendation="Advance",
                            agrees_with_ai=True, decided_by="user:1"))
            db.commit()
        return a.id


def _item(c, app_id):
    return next((i for i in c.get("/followups").json()["items"] if i["application_id"] == app_id), None)


def _invited(c) -> int:
    app_id = _app(ApplicationStatus.SHORTLISTED)
    draft_id = c.post(f"/candidates/{app_id}/invite").json()["draft_id"]
    assert _item(c, app_id) is None  # invitation not sent yet: nothing to follow up
    c.post(f"/approvals/{draft_id}/approve")
    return app_id


def _portal_token(c, draft_id) -> str:
    body = c.get("/approvals?status=all").json()
    d = next(x for x in body if x["id"] == draft_id)
    return d["body"].split("/portal/")[1].split()[0]


def test_answers_reminder_flow():
    c = logged_in_client()
    fu.set_demo_shift(0)
    app_id = _invited(c)
    it = _item(c, app_id)
    assert it["state"] == "waiting" and it["kind"] == "answers" and it["reminders_sent"] == 0

    fu.set_demo_shift(settings.followup_after_hours + 1)
    try:
        assert _item(c, app_id)["state"] == "due"
        r = c.post("/followups/remind_due").json()
        assert r["drafted"] >= 1
        draft_id = _item(c, app_id)["pending_draft_id"]
        assert draft_id and _item(c, app_id)["state"] == "drafted"
        # the reminder's new link does NOT work before HR approves it
        token = _portal_token(c, draft_id)
        assert c.get(f"/portal/{token}").status_code != 200
        # visible on the candidate page (inline approval)
        assert any(d["id"] == draft_id for d in c.get(f"/candidates/{app_id}").json()["pending_drafts"])
        c.post(f"/approvals/{draft_id}/approve")
        assert c.get(f"/portal/{token}").status_code == 200  # now it works
        it = _item(c, app_id)
        assert it["reminders_sent"] == 1 and it["state"] == "waiting"  # clock restarts after each contact
    finally:
        fu.set_demo_shift(0)


def _later():
    fu.set_demo_shift(fu.demo_shift() + settings.followup_after_hours + 1)


def test_no_early_reminders():
    c = logged_in_client()
    fu.set_demo_shift(0)
    app_id = _invited(c)
    r = c.post(f"/followups/{app_id}/remind")
    assert r.status_code == 400 and "Not due yet" in r.json()["detail"]
    assert _item(c, app_id)["can_remind"] is False
    _later()
    try:
        assert _item(c, app_id)["can_remind"] is True
        d = c.post(f"/followups/{app_id}/remind").json()["draft_id"]
        c.post(f"/approvals/{d}/approve")
        it = _item(c, app_id)
        # just reminded: no "remind again" until the waiting period has passed again
        assert it["state"] == "waiting" and it["can_remind"] is False and "Reminder 1 sent" in it["reason"]
        assert c.post(f"/followups/{app_id}/remind").status_code == 400
    finally:
        fu.set_demo_shift(0)


def test_rejected_reminder_link_never_works():
    c = logged_in_client()
    fu.set_demo_shift(0)
    app_id = _invited(c)
    _later()
    try:
        draft_id = c.post(f"/followups/{app_id}/remind").json()["draft_id"]
    finally:
        fu.set_demo_shift(0)
    token = _portal_token(c, draft_id)
    c.post(f"/approvals/{draft_id}/reject")
    assert c.get(f"/portal/{token}").status_code != 200
    with Session(engine) as db:
        assert not db.exec(select(SentEmail).where(SentEmail.draft_id == draft_id)).first()


def test_max_reminders_then_your_call_and_close():
    c = logged_in_client()
    fu.set_demo_shift(0)
    app_id = _invited(c)
    try:
        for _ in range(settings.followup_max_reminders):
            _later()
            d = c.post(f"/followups/{app_id}/remind").json()["draft_id"]
            c.post(f"/approvals/{d}/approve")
        last = c.get("/approvals?status=all").json()
        assert "Last reminder" in next(x for x in last if x["id"] == d)["subject"]
        _later()
        assert _item(c, app_id)["state"] == "your_call"
        r = c.post(f"/followups/{app_id}/remind")
        assert r.status_code == 400  # no endless reminders
    finally:
        fu.set_demo_shift(0)

    r = c.post(f"/followups/{app_id}/close", json={"note": ""})
    assert r.status_code == 200
    with Session(engine) as db:
        app = db.get(Application, app_id)
        assert app.status == ApplicationStatus.DECIDED
        dec = db.exec(select(Decision).where(Decision.application_id == app_id)).first()
        assert dec.decision == "reject" and "no response" in dec.note.lower()
        closing = db.get(Draft, r.json()["draft_id"])
        assert closing.status == DraftStatus.PENDING and closing.type == DraftType.REJECTION  # still needs a click
    assert _item(c, app_id) is None


def test_schedule_reminder_new_link():
    c = logged_in_client()
    app_id = _app(ApplicationStatus.DECIDED, advanced=True)
    first = c.post(f"/candidates/{app_id}/schedule/new").json()["draft_id"]
    c.post(f"/approvals/{first}/approve")
    assert _item(c, app_id)["kind"] == "schedule"
    fu.set_demo_shift(0)
    _later()
    d = c.post(f"/followups/{app_id}/remind").json()["draft_id"]
    body = next(x for x in c.get("/approvals").json() if x["id"] == d)["body"]
    token = body.split("/schedule/")[1].split()[0]
    assert c.get(f"/schedule/{token}").status_code == 404  # locked until sent
    assert _item(c, app_id)["state"] == "drafted"
    c.post(f"/approvals/{d}/approve")
    assert c.get(f"/schedule/{token}").status_code == 200
    assert _item(c, app_id)["reminders_sent"] == 1

    # a rejected scheduling reminder leaves the previous invitation in place
    _later()
    d2 = c.post(f"/followups/{app_id}/remind").json()["draft_id"]
    c.post(f"/approvals/{d2}/reject")
    with Session(engine) as db:
        assert not db.exec(select(ScheduleOffer).where(ScheduleOffer.draft_id == d2)).first()
    assert _item(c, app_id)["state"] == "due"  # still due: nothing was sent
    fu.set_demo_shift(0)


def test_demo_clock_is_dev_only_and_changes_no_data():
    c = logged_in_client()
    assert c.post("/followups/demo_clock", json={"hours": 72}).json()["demo_shift_hours"] == 72
    c.post("/followups/demo_clock", json={"hours": 0})
    old = settings.app_env
    settings.app_env = "prod"
    try:
        assert c.post("/followups/demo_clock", json={"hours": 72}).status_code == 403
    finally:
        settings.app_env = old
