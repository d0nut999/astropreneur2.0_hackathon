"""Email triage pipeline: one incoming email -> security gate -> AI analysis -> urgency rules -> database.

Nothing here sends, forwards or deletes anything. It only records what it found.
"""
import secrets
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from ..audit import log_audit
from ..config import settings
from ..models import (
    Application, ApplicationStatus, Candidate, Email, Event, EventType, Job,
)
from ..state_machine import transition
from .classifier import analyze_email
from .security_gate import check_upload
from .urgency import decide_urgency

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"


def process_incoming(db: Session, raw: dict, now: datetime | None = None) -> Email | None:
    """Analyze and store one email. Returns None if it was already imported."""
    now = now or datetime.now()
    if raw.get("message_id"):
        exists = db.exec(select(Email).where(Email.message_id == raw["message_id"])).first()
        if exists:
            return None

    # 1. Security gate on attachments (before any AI reads anything)
    saved, security_flags = _save_and_check_attachments(raw.get("attachments", []))

    # 2. AI analysis (or offline rules if the AI is unavailable)
    analysis, source = analyze_email(raw, now, db)

    # 3. Final urgency decided by rules in code
    urgency, reasons = decide_urgency(
        analysis,
        sender=raw["from_addr"],
        sender_name=raw.get("from_name", ""),
        text=f"{raw['subject']}\n{raw['body']}",
        now=now,
        vip_list=settings.vip_sender_list,
        security_flags=security_flags,
    )

    # A new meeting request that clashes with an interview must be seen quickly
    if analysis.meeting and analysis.meeting.date and analysis.meeting.time and urgency != "flagged":
        from .scheduler import interview_conflict
        try:
            start = datetime.strptime(f"{analysis.meeting.date} {analysis.meeting.time}", "%Y-%m-%d %H:%M")
            slot = interview_conflict(db, start)
        except ValueError:
            slot = None
        if slot:
            urgency = "urgent"
            reasons = [f"Clashes with the interview of Candidate #{slot.application_id:03d} at {slot.start:%H:%M}"] + \
                [r for r in reasons if not r.startswith("Information only")]

    email_row = Email(
        message_id=raw.get("message_id", ""),
        from_name=raw.get("from_name", ""),
        from_addr=raw["from_addr"],
        to_addr=raw.get("to_addr", ""),
        subject=raw["subject"],
        body=raw["body"],
        attachments_json=[{k: v for k, v in a.items() if k != "path"} for a in saved],
        received_at=raw["received_at"],
        category=analysis.category,
        summary=analysis.summary,
        urgency=urgency,
        urgency_reasons_json=reasons,
        needs_human=analysis.needs_human_reply or urgency in {"urgent", "flagged"},
        injection_suspected=analysis.injection_suspected,
        injection_text=analysis.injection_text,
        security_flags_json=security_flags,
        analysis_source=source,
    )
    db.add(email_row)
    db.commit()
    db.refresh(email_row)

    # 4. Meetings & deadlines -> suggested events (HR confirms or dismisses)
    if analysis.meeting and analysis.meeting.date and urgency != "flagged":
        m = analysis.meeting
        db.add(Event(email_id=email_row.id, type=EventType.MEETING, title=m.title or raw["subject"],
                     date=m.date, time=m.time, location=m.location, attendees_json=m.with_people))
    if analysis.deadline and urgency != "flagged":
        db.add(Event(email_id=email_row.id, type=EventType.DEADLINE,
                     title=analysis.deadline_what or raw["subject"], date=analysis.deadline))
    db.commit()

    # 5. Job applications with a CV -> create a candidate application (screened or quarantined)
    if analysis.category == "candidate_application":
        cv = next((a for a in saved if a["filename"].lower().endswith((".pdf", ".docx"))), None)
        if cv:
            app = _create_application(db, raw, cv)
            email_row.application_id = app.id
            db.add(email_row)
            db.commit()

    log_audit(db, actor="ai" if source == "ai" else "system", action="triage_email", entity="email",
              entity_id=email_row.id, payload={"category": email_row.category, "urgency": urgency})
    return email_row


def _save_and_check_attachments(attachments: list[dict]) -> tuple[list[dict], list[str]]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved, flags = [], []
    for a in attachments:
        original = Path(a["filename"]).name  # strip any path tricks
        suffix = Path(original).suffix.lower()[:6]
        path = UPLOAD_DIR / f"{secrets.token_hex(12)}{suffix}"  # random name, never the user's
        path.write_bytes(a["content"])
        result = check_upload(path)
        item = {"filename": original, "path": str(path), "safe": result.is_safe,
                "flags": result.flags, "hidden_text": result.hidden_text[:5]}
        saved.append(item)
        flags += [f"{original}: {f}" for f in result.flags]
    return saved, flags


def _create_application(db: Session, raw: dict, cv: dict) -> Application:
    job = db.exec(select(Job)).first()
    if not job:
        job = Job(title="General application", description="Applications received by email")
        db.add(job)
        db.commit()
        db.refresh(job)

    candidate = db.exec(select(Candidate).where(Candidate.email == raw["from_addr"])).first()
    if not candidate:
        candidate = Candidate(name=raw.get("from_name") or raw["from_addr"], email=raw["from_addr"])
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

    app = Application(
        job_id=job.id,
        candidate_id=candidate.id,
        cv_path=cv["path"],
        security_flags_json={"flags": cv["flags"], "hidden_text": cv["hidden_text"]},
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    target = ApplicationStatus.SCREENED if cv["safe"] else ApplicationStatus.QUARANTINED
    app = transition(db, app, target, actor="system")
    if app.status == ApplicationStatus.SCREENED:
        try:
            from .scorer import score_application
            score_application(db, app)
        except Exception as e:  # scoring must never break email import
            print(f"[triage] could not score application {app.id}: {e}")
    return app
