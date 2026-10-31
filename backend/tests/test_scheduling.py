"""Interview scheduling: free slots, holds, booking, refusal, clashes."""
import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine, init_db
from app.main import app
from app.models import (
    Application, ApplicationStatus, Candidate, Decision, Email, Event, EventType, InterviewSlot, Job, ScheduleOffer,
    SlotStatus,
)
from app.services.scheduler import expire_stale, find_free_slots, parse_availability
from app.services.triage import process_incoming
from tests.conftest import logged_in_client


def _advanced_candidate() -> int:
    init_db()
    with Session(engine) as db:
        job = Job(title="Sched job", description="Python")
        db.add(job)
        db.commit()
        cand = Candidate(name="Sched Person", email=f"s-{uuid.uuid4().hex[:8]}@example.com")
        db.add(cand)
        db.commit()
        a = Application(job_id=job.id, candidate_id=cand.id, status=ApplicationStatus.DECIDED)
        db.add(a)
        db.commit()
        db.add(Decision(application_id=a.id, decision="advance", ai_recommendation="Advance", agrees_with_ai=True,
                        decided_by="user:1"))
        db.commit()
        return a.id


def _offer(c: TestClient, app_id: int) -> tuple[str, dict]:
    draft_id = c.post(f"/candidates/{app_id}/schedule/new").json()["draft_id"]
    st = c.get(f"/candidates/{app_id}").json()["scheduling"]
    token = st["link"].rsplit("/", 1)[1]
    assert c.get(f"/schedule/{token}").status_code == 404      # locked until HR approves
    c.post(f"/approvals/{draft_id}/approve")
    return token, c.get(f"/schedule/{token}").json()


def test_free_slots_avoid_meetings_and_weekends():
    init_db()
    with Session(engine) as db:
        first = find_free_slots(db, count=1)[0]
        db.add(Email(from_addr="x@fictional-company.test", subject="t", body="t"))
        db.commit()
        email = db.exec(select(Email)).first()
        ev = Event(email_id=email.id, type=EventType.MEETING, title="Blocking meeting",
                   date=first.strftime("%Y-%m-%d"), time=first.strftime("%H:%M"))
        db.add(ev)
        db.commit()
        slots = find_free_slots(db, count=3)
        assert first not in slots
        assert all(s.weekday() < 5 for s in slots)
        assert all(not (12 <= s.hour < 13) for s in slots)  # never during lunch
        db.delete(ev)
        db.commit()


def test_book_releases_other_slots_and_gives_calendar_file():
    c = logged_in_client()
    app_id = _advanced_candidate()
    token, offer = _offer(c, app_id)
    assert len(offer["slots"]) == 3 and offer["status"] == "pending"
    r = c.post(f"/schedule/{token}/book", json={"slot_id": offer["slots"][1]["id"]})
    assert r.status_code == 200
    statuses = [s["status"] for s in c.get(f"/candidates/{app_id}").json()["scheduling"]["slots"]]
    assert statuses.count("booked") == 1 and statuses.count("released") == 2
    assert "BEGIN:VCALENDAR" in c.get(f"/candidates/{app_id}/interview.ics").text
    assert c.post(f"/schedule/{token}/book", json={"slot_id": offer["slots"][0]["id"]}).status_code == 410  # once


def test_decline_then_new_slots_follow_availability():
    c = logged_in_client()
    app_id = _advanced_candidate()
    token, _ = _offer(c, app_id)
    assert c.post(f"/schedule/{token}/decline", json={"availability": "Only afternoons please"}).status_code == 200
    token2, offer2 = _offer(c, app_id)
    hours = [datetime.fromisoformat(s["start"]).hour for s in offer2["slots"]]
    assert all(h >= 13 for h in hours)


def test_rejected_email_releases_held_slots():
    c = logged_in_client()
    app_id = _advanced_candidate()
    draft_id = c.post(f"/candidates/{app_id}/schedule/new").json()["draft_id"]
    c.post(f"/approvals/{draft_id}/reject")
    slots = c.get(f"/candidates/{app_id}").json()["scheduling"]["slots"]
    assert all(s["status"] == "released" for s in slots)


def test_new_meeting_on_an_interview_is_flagged_and_confirm_warns():
    c = logged_in_client()
    app_id = _advanced_candidate()
    token, offer = _offer(c, app_id)
    c.post(f"/schedule/{token}/book", json={"slot_id": offer["slots"][0]["id"]})
    start = datetime.fromisoformat(offer["slots"][0]["start"])
    with Session(engine) as db:
        email = process_incoming(db, {
            "message_id": f"clash-{uuid.uuid4().hex}", "from_name": "Colleague",
            "from_addr": "colleague@fictional-company.test", "subject": "Quick meeting",
            "body": f"Can we have a meeting on {start:%Y-%m-%d} at {start:%H:%M}?",
            "received_at": datetime.now(), "attachments": []})
        assert email.urgency == "urgent"
        assert any("Clashes with the interview" in r for r in email.urgency_reasons_json)
        event_id = db.exec(select(Event).where(Event.email_id == email.id)).first().id
    assert c.post(f"/events/{event_id}/confirm").status_code == 409
    assert c.post(f"/events/{event_id}/confirm?force=true").status_code == 200


def test_unanswered_offer_expires_and_frees_the_calendar():
    c = logged_in_client()
    app_id = _advanced_candidate()
    token, _ = _offer(c, app_id)
    with Session(engine) as db:
        offer = db.exec(select(ScheduleOffer).where(ScheduleOffer.application_id == app_id)).first()
        offer.expires_at = datetime.now() - timedelta(minutes=1)
        db.add(offer)
        db.commit()
        expire_stale(db)
        held = db.exec(select(InterviewSlot).where(InterviewSlot.offer_id == offer.id,
                                                   InterviewSlot.status == SlotStatus.HELD)).all()
        assert held == []
    assert c.get(f"/schedule/{token}").status_code == 410


def test_parse_availability():
    p = parse_availability("Tuesday or Thursday afternoon, next week", datetime(2026, 10, 31))
    assert p["days"] == {1, 3} and p["parts"] == {"afternoon"} and p["next_week"]
