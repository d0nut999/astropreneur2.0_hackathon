"""Interview scheduling: blocks, first come first served, no double booking, refusals, clashes."""
import threading
import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.db import engine, init_db
from app.main import app
from app.models import (
    Application, ApplicationStatus, Candidate, Decision, Email, Event, EventType, InterviewSlot, Job, ScheduleOffer,
    SlotStatus,
)
from app.services import scheduler
from app.services.triage import process_incoming
from tests.conftest import logged_in_client


def _clear_bookings():
    init_db()
    with Session(engine) as db:
        for s in db.exec(select(InterviewSlot)).all():
            db.delete(s)
        db.commit()


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


def _link(c: TestClient, app_id: int) -> tuple[str, dict]:
    draft_id = c.post(f"/candidates/{app_id}/schedule/new").json()["draft_id"]
    token = c.get(f"/candidates/{app_id}").json()["scheduling"]["link"].rsplit("/", 1)[1]
    assert c.get(f"/schedule/{token}").status_code == 404  # locked until HR approves
    c.post(f"/approvals/{draft_id}/approve")
    return token, c.get(f"/schedule/{token}").json()


def test_times_only_inside_interview_blocks():
    _clear_bookings()
    with Session(engine) as db:
        times = scheduler.free_times(db, horizon_days=14)
    allowed = scheduler.blocks()
    assert times
    for t in times:
        assert any(s <= t.hour < e for s, e in allowed.get(t.weekday(), []))
        assert not (settings.lunch_start <= t.hour < settings.lunch_end)
        assert t >= datetime.now() + timedelta(hours=settings.min_notice_hours)


def test_nothing_is_reserved_until_booked():
    _clear_bookings()
    c = logged_in_client()
    with Session(engine) as db:
        before = scheduler.capacity(db, days=14)
    _link(c, _advanced_candidate())
    _link(c, _advanced_candidate())
    with Session(engine) as db:
        assert scheduler.capacity(db, days=14) == before  # invitations don't block the calendar


def test_first_come_first_served_and_alternatives():
    _clear_bookings()
    c = logged_in_client()
    t1, o1 = _link(c, _advanced_candidate())
    t2, o2 = _link(c, _advanced_candidate())
    same = o1["times"][0]
    assert same in o2["times"]                                    # both see the same live time
    assert c.post(f"/schedule/{t1}/book", json={"start": same}).status_code == 200
    r = c.post(f"/schedule/{t2}/book", json={"start": same})
    assert r.status_code == 409                                   # second one is refused...
    assert r.json()["detail"]["alternatives"]                     # ...and gets the closest free times
    assert same not in c.get(f"/schedule/{t2}").json()["times"]   # and the time disappeared from their page


def test_two_simultaneous_bookings_never_double_book():
    _clear_bookings()
    ids = [_advanced_candidate() for _ in range(5)]
    with Session(engine) as db:
        target = scheduler.free_times(db, limit=1)[0]
    results = []

    def attempt(app_id):
        with Session(engine) as db:
            try:
                scheduler.book_time(db, app_id, target, actor="candidate")
                results.append("ok")
            except scheduler.SlotTaken:
                results.append("taken")

    threads = [threading.Thread(target=attempt, args=(i,)) for i in ids]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count("ok") == 1 and results.count("taken") == 4
    with Session(engine) as db:
        assert len(db.exec(select(InterviewSlot).where(InterviewSlot.start == target)).all()) == 1


def test_max_interviews_per_day():
    _clear_bookings()
    with Session(engine) as db:
        first = scheduler.free_times(db, limit=1)[0]
        day_times = [t for t in scheduler.free_times(db, horizon_days=21) if t.date() == first.date()]
    if len(day_times) <= settings.max_interviews_per_day:
        return  # block too short to test the cap with the current settings
    with Session(engine) as db:
        for t in day_times[: settings.max_interviews_per_day]:
            scheduler.book_time(db, _advanced_candidate(), t, actor="test")
        left = [t for t in scheduler.free_times(db, horizon_days=21) if t.date() == first.date()]
    assert left == []


def test_meeting_from_email_blocks_a_time():
    _clear_bookings()
    with Session(engine) as db:
        first = scheduler.free_times(db, limit=1)[0]
        db.add(Email(from_addr="x@fictional-company.test", subject="t", body="t"))
        db.commit()
        email = db.exec(select(Email)).first()
        ev = Event(email_id=email.id, type=EventType.MEETING, title="Blocking meeting",
                   date=first.strftime("%Y-%m-%d"), time=first.strftime("%H:%M"))
        db.add(ev)
        db.commit()
        assert first not in scheduler.free_times(db, horizon_days=21)
        db.delete(ev)
        db.commit()


def test_decline_then_new_link_shows_preferred_times_first():
    _clear_bookings()
    c = logged_in_client()
    app_id = _advanced_candidate()
    token, _ = _link(c, app_id)
    assert c.post(f"/schedule/{token}/decline", json={"availability": "Only mornings please"}).status_code == 200
    _, offer2 = _link(c, app_id)
    first_hour = datetime.fromisoformat(offer2["times"][0]).hour
    assert first_hour < 12


def test_rejected_scheduling_email_cancels_the_link():
    c = logged_in_client()
    app_id = _advanced_candidate()
    draft_id = c.post(f"/candidates/{app_id}/schedule/new").json()["draft_id"]
    c.post(f"/approvals/{draft_id}/reject")
    assert c.get(f"/candidates/{app_id}").json()["scheduling"]["status"] == "cancelled"


def test_new_meeting_on_an_interview_is_flagged_and_confirm_warns():
    _clear_bookings()
    c = logged_in_client()
    app_id = _advanced_candidate()
    token, offer = _link(c, app_id)
    start = datetime.fromisoformat(offer["times"][0])
    c.post(f"/schedule/{token}/book", json={"start": offer["times"][0]})
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


def test_old_link_expires():
    c = logged_in_client()
    app_id = _advanced_candidate()
    token, _ = _link(c, app_id)
    with Session(engine) as db:
        offer = db.exec(select(ScheduleOffer).where(ScheduleOffer.application_id == app_id)).first()
        offer.expires_at = datetime.now() - timedelta(minutes=1)
        db.add(offer)
        db.commit()
    assert c.get(f"/schedule/{token}").status_code == 410


def test_parse_availability():
    p = scheduler.parse_availability("Tuesday or Thursday afternoon, next week", datetime(2026, 10, 31))
    assert p["days"] == {1, 3} and p["parts"] == {"afternoon"} and p["next_week"]


def test_two_candidates_email_for_the_same_time():
    _clear_bookings()
    c = logged_in_client()
    a1, a2 = _advanced_candidate(), _advanced_candidate()
    with Session(engine) as db:
        emails = [db.get(Candidate, db.get(Application, a).candidate_id).email for a in (a1, a2)]
        t = scheduler.free_times(db, limit=1)[0]
    body = f"Hello, would {t:%A} at {t:%H:%M} work for my interview?"
    for e in emails:
        r = c.post("/emails/simulate", json={"from_addr": e, "subject": "Interview time", "body": body}).json()
        assert "free" in r["urgency_reasons"][0]
    r1 = c.get(f"/candidates/{a1}").json()["scheduling"]["requests"][0]
    r2 = c.get(f"/candidates/{a2}").json()["scheduling"]["requests"][0]
    assert c.post(f"/candidates/{a1}/schedule/requests/{r1['id']}/book").status_code == 200
    second = c.post(f"/candidates/{a2}/schedule/requests/{r2['id']}/book")
    assert second.status_code == 409 and second.json()["detail"]["alternatives"]
    assert not any(e["type"] == "meeting" and e["date"] == t.strftime("%Y-%m-%d") and e["time"] == t.strftime("%H:%M")
                   for e in c.get("/events").json())  # a candidate's email never blocks the calendar itself



def test_calendar_week_shows_interviews_blocks_and_free_spots():
    _clear_bookings()
    c = logged_in_client()
    app_id = _advanced_candidate()
    token, offer = _link(c, app_id)
    start = offer["times"][0]
    c.post(f"/schedule/{token}/book", json={"start": start})
    week = c.get(f"/calendar?day={start[:10]}").json()
    assert any(i["kind"] == "interview" and i["start"] == start for i in week["items"])
    assert any(d["blocks"] for d in week["days"])
    assert start not in week["free_spots"]
    assert week["summary"]["interviews"] >= 1
    assert "Tue" in week["settings"]["blocks_text"]
