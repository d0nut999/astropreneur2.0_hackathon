"""Employees & leave: rules in code, human decisions, handbook answers that cite or forward."""
from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from app.config import settings
from app.db import engine, init_db
from app.models import Draft, Email, Employee, LeaveRequest, LeaveStatus, LeaveType
from app.services import employees as E
from app.services import leave as L
from app.services.triage import process_incoming
from tests.conftest import logged_in_client

TODAY = date.today()


def _fresh():
    init_db()
    settings.llm_api_key = ""  # offline rules: deterministic tests
    with Session(engine) as db:
        E.seed_employees(db)


def _emp(db, name) -> Employee:
    return db.exec(select(Employee).where(Employee.name == name)).first()


def _request(db, name, start, end, kind=LeaveType.ANNUAL) -> LeaveRequest:
    r = LeaveRequest(employee_id=_emp(db, name).id, type=kind, start=start, end=end)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_workdays_and_date_reading():
    assert len(L.workdays(date(2026, 11, 2), date(2026, 11, 8))) == 5  # Mon..Sun -> 5 working days
    s, e = L.parse_dates("I would like leave from 9 to 13 November please", date(2026, 10, 31))
    assert (s, e) == (date(2026, 11, 9), date(2026, 11, 13))
    s, e = L.parse_dates("Could I take leave on Monday 16 November for three days?", date(2026, 10, 31))
    assert (s, e) == (date(2026, 11, 16), date(2026, 11, 18))
    assert L.leave_type_of("I am sick, the doctor gave me 2 days") == LeaveType.SICK


def test_recommendations_follow_the_rules():
    _fresh()
    with Session(engine) as db:
        mon1, fri1 = L.week_day(TODAY, 1, 0), L.week_day(TODAY, 1, 4)
        # Customer Support: Nour is already off next week -> Hatem the same week = 4/6 = 67% < 70%
        ev = L.evaluate(db, _request(db, "Hatem Riahi", mon1, fri1))
        assert ev["recommendation"] == "move" and ev["min_presence"] < 70
        assert ev["alternatives"] and all(a["min_presence"] >= 70 for a in ev["alternatives"])
        # Mehdi has used 28/30 -> 4 more days = over the limit
        ev = L.evaluate(db, _request(db, "Mehdi Saidi", L.week_day(TODAY, 2, 0), L.week_day(TODAY, 2, 3)))
        assert ev["recommendation"] == "over_limit" and ev["annual_used"] == 28
        # Sick leave is never refused for staffing; above 60 days it is flagged
        ev = L.evaluate(db, _request(db, "Walid Gharbi", mon1, L.week_day(TODAY, 1, 2), LeaveType.SICK))
        assert ev["recommendation"] == "sick_alert" and ev["sick_used"] == 58
        ev = L.evaluate(db, _request(db, "Nour Kefi", L.week_day(TODAY, 1, 0), L.week_day(TODAY, 1, 0), LeaveType.SICK))
        assert ev["recommendation"] in ("approve", "sick_alert")  # never "move"
        # normal request
        ev = L.evaluate(db, _request(db, "Amira Sassi", L.week_day(TODAY, 3, 2), L.week_day(TODAY, 3, 3)))
        assert ev["recommendation"] == "approve"


def test_human_decisions_need_reasons_and_create_reply_drafts():
    _fresh()
    c = logged_in_client()
    with Session(engine) as db:
        mehdi = _request(db, "Mehdi Saidi", L.week_day(TODAY, 2, 0), L.week_day(TODAY, 2, 3)).id
        amira = _request(db, "Amira Sassi", L.week_day(TODAY, 3, 2), L.week_day(TODAY, 3, 3)).id
    # approving over the limit = going against the recommendation -> reason required
    r = c.post(f"/employees/leave/{mehdi}/decide", json={"action": "approve"})
    assert r.status_code == 422
    # any rejection needs a reason
    assert c.post(f"/employees/leave/{amira}/decide", json={"action": "reject"}).status_code == 422
    # decline + meeting -> reply drafted, NOT sent
    r = c.post(f"/employees/leave/{mehdi}/decide", json={"action": "meeting"})
    assert r.status_code == 200
    with Session(engine) as db:
        d = db.get(Draft, r.json()["draft_id"])
        assert d.status == "pending" and "meeting" in d.body and d.to_addr == "mehdi.saidi@fictional-company.test"
        assert db.get(LeaveRequest, mehdi).status == LeaveStatus.REJECTED
    # approving updates the balance
    r = c.post(f"/employees/leave/{amira}/decide", json={"action": "approve"})
    assert r.status_code == 200
    with Session(engine) as db:
        assert L.days_used(db, _emp(db, "Amira Sassi").id, LeaveType.ANNUAL, L.week_day(TODAY, 3, 2).year) >= 2
    assert c.post(f"/employees/leave/{amira}/decide", json={"action": "reject", "note": "x" * 20}).status_code == 422  # already decided


def test_leave_email_from_unknown_sender_is_ignored():
    _fresh()
    with Session(engine) as db:
        raw = {"from_name": "Stranger", "from_addr": "someone@outside.test", "subject": "Leave request",
               "body": f"I would like leave from {L.human(L.week_day(TODAY, 2, 0))} to {L.human(L.week_day(TODAY, 2, 1))}.",
               "received_at": datetime.now(), "message_id": f"<x-{datetime.now().timestamp()}>"}
        row = process_incoming(db, raw)
        assert row.category != "leave_request"
        assert not db.exec(select(LeaveRequest).where(LeaveRequest.email_id == row.id)).first()


def test_leave_email_from_employee_creates_request():
    _fresh()
    with Session(engine) as db:
        start = L.week_day(TODAY, 3, 1)
        raw = {"from_name": "Amira Sassi", "from_addr": "amira.sassi@fictional-company.test", "subject": "Leave request",
               "body": f"Hello, I would like to take leave on {L.human(start)} for a family event. Thanks",
               "received_at": datetime.now(), "message_id": f"<y-{datetime.now().timestamp()}>"}
        row = process_incoming(db, raw)
        assert row.category == "leave_request" and row.urgency != "low"
        req = db.exec(select(LeaveRequest).where(LeaveRequest.email_id == row.id)).first()
        assert req.start == start and req.status == LeaveStatus.PENDING  # nothing decided automatically


def test_handbook_answers_cite_or_forward():
    _fresh()
    with Session(engine) as db:
        omar = _emp(db, "Omar Jaziri")
        a = E.answer_question(db, "Can I work remotely two days a week? How many leave days do I have left?", omar)
        assert a["answered"] and not a["forwarded"]
        assert {s["n"] for s in a["sections"]} >= {1, 4}
        used = L.days_used(db, omar.id, LeaveType.ANNUAL, TODAY.year)
        assert f"used {used} of your {settings.annual_leave_days}" in a["answer"]  # balance comes from data, not the AI
        b = E.answer_question(db, "Can I bring my dog to the office?", None)
        assert b["forwarded"] and not b["answered"]  # not in the handbook -> HR, no guessing


def test_question_email_gets_a_draft_reply_not_sent():
    _fresh()
    with Session(engine) as db:
        raw = {"from_name": "Sarra Ellouze", "from_addr": "sarra.ellouze@fictional-company.test",
               "subject": "Training", "body": "Hi, is there a training budget I can use this year?",
               "received_at": datetime.now(), "message_id": f"<z-{datetime.now().timestamp()}>"}
        row = process_incoming(db, raw)
        assert row.category == "employee_question"
        d = db.exec(select(Draft).where(Draft.email_id == row.id)).first()
        assert d.status == "pending" and "§7" in d.body


def test_overview_counts():
    _fresh()
    c = logged_in_client()
    o = c.get("/employees/overview").json()
    assert o["total"] == 40
    assert o["working"] + o["on_annual"] + o["on_sick"] == 40
    assert all(0 <= t["presence"] <= 100 for t in o["teams"])
    from fastapi.testclient import TestClient
    from app.main import app
    assert TestClient(app).get("/employees/overview").status_code == 401  # staff data needs login
