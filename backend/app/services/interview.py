"""Written interview: questions, one-time secure link, invitation draft.

Fairness: 2 standard questions are identical for every candidate of a job (comparable answers),
plus 1 question tailored to the candidate's weakest job criterion.
Security: the link contains a random token; only its SHA-256 hash is stored. It expires and works once.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from sqlmodel import Session, select

from ..audit import log_audit
from ..config import settings
from ..llm import LLMError, complete_json
from ..models import (
    Application, ApplicationStatus, Candidate, Draft, DraftStatus, DraftType,
    InterviewQuestion, Job, Score, VideoSubmission,
)
from ..schemas import TailoredQuestion

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "tailored_question.md"

STANDARD_QUESTIONS = [
    {
        "text": "Describe a backend feature or API you built. What did it do, which technologies did you use "
                "(framework, database), and what was the hardest problem you solved?",
        "rubric": "Concrete project; names the framework and database; explains a real technical problem and "
                  "how it was solved; shows ownership.",
    },
    {
        "text": "How do you make sure your code works correctly before it reaches users? "
                "Give a concrete example (tests, code review, CI, monitoring...).",
        "rubric": "Mentions automated tests or a clear verification method; gives a real example; "
                  "understands why quality matters.",
    },
]


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def standard_questions(db: Session, job: Job) -> list[InterviewQuestion]:
    """Same questions for every candidate of this job (created once)."""
    rows = db.exec(select(InterviewQuestion).where(
        InterviewQuestion.job_id == job.id, InterviewQuestion.application_id == None,  # noqa: E711
    )).all()
    if not rows:
        rows = [InterviewQuestion(job_id=job.id, application_id=None, text=q["text"], rubric=q["rubric"])
                for q in STANDARD_QUESTIONS]
        for r in rows:
            db.add(r)
        db.commit()
        for r in rows:
            db.refresh(r)
    return list(rows)


def tailored_question(db: Session, app: Application, job: Job) -> InterviewQuestion:
    """One question about the candidate's weakest criterion (AI, with a safe fallback)."""
    existing = db.exec(select(InterviewQuestion).where(InterviewQuestion.application_id == app.id)).first()
    if existing:
        return existing

    score = db.exec(select(Score).where(Score.application_id == app.id).order_by(Score.id.desc())).first()
    crit = sorted(score.criteria_json.get("criteria", []), key=lambda c: (c["score"], -c["weight"])) if score else []
    weakest = crit[0] if crit else {"label": "the main skills of this job", "description": ""}
    gaps = score.criteria_json.get("gaps", []) if score else []

    try:
        user = (
            f"<job>{job.title}</job>\n"
            f"Weakest criterion: {weakest['label']} (score {weakest.get('score', '?')}/5)\n"
            f"Gaps noted: {', '.join(gaps) or 'none'}\n\n"
            f"<resume_data>\n{app.anonymized_profile_json.get('text', '')[:6000]}\n</resume_data>"
        )
        q = complete_json(task="tailored_question", system=PROMPT_PATH.read_text(encoding="utf-8"), user=user,
                          schema=TailoredQuestion, prompt_version="question_v1", db=db)
        text, rubric = q.question.strip()[:600], q.rubric.strip()[:600]
    except LLMError:
        text = (f"This role needs {weakest['label']}. Tell us about your experience with it, or, if it "
                f"is new to you, explain concretely how you would get up to speed in your first month.")
        rubric = "Honest and concrete; real examples or a realistic learning plan; relevant to the job."

    row = InterviewQuestion(job_id=job.id, application_id=app.id, text=text, rubric=rubric, is_tailored=True)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def questions_for(db: Session, app: Application) -> list[InterviewQuestion]:
    job = db.get(Job, app.job_id)
    tailored = db.exec(select(InterviewQuestion).where(InterviewQuestion.application_id == app.id)).all()
    return standard_questions(db, job) + list(tailored)


def prepare_invitation(db: Session, app: Application, actor: str) -> Draft:
    """Create questions + secure link + invitation DRAFT (goes to Approvals; nothing is sent)."""
    if app.status != ApplicationStatus.SHORTLISTED:
        raise ValueError("Only shortlisted candidates can be invited.")

    pending = db.exec(select(Draft).where(Draft.application_id == app.id, Draft.type == DraftType.INVITE,
                                          Draft.status == DraftStatus.PENDING)).first()
    if pending:
        return pending

    job = db.get(Job, app.job_id)
    cand = db.get(Candidate, app.candidate_id)
    standard_questions(db, job)
    tailored_question(db, app, job)
    questions = questions_for(db, app)

    # New one-time link (any older unused link for this application is disabled)
    for old in db.exec(select(VideoSubmission).where(VideoSubmission.application_id == app.id,
                                                     VideoSubmission.used == False)).all():  # noqa: E712
        old.used = True
        db.add(old)
    token = secrets.token_urlsafe(32)
    db.add(VideoSubmission(application_id=app.id, path="", token_hash=hash_token(token),
                           expires_at=datetime.now() + timedelta(hours=settings.portal_token_ttl_hours)))

    link = f"{settings.frontend_url.rstrip('/')}/portal/{token}"
    first = (cand.name or "").split(" ")[0] or "there"
    q_list = "\n".join(f"{i}. {q.text}" for i, q in enumerate(questions, 1))
    body = (
        f"Hello {first},\n\n"
        f"Thank you for applying for the {job.title} position. We enjoyed reading your application and "
        f"would like to invite you to the next step: a short written interview with {len(questions)} questions.\n\n"
        f"Please answer here (personal link, valid {settings.portal_token_ttl_hours} hours, can be used once):\n"
        f"{link}\n\n"
        f"The questions:\n{q_list}\n\n"
        f"There is no trick: we only look at the content of your answers. Take your time.\n\n"
        f"Best regards,\nHR Team"
    )
    draft = Draft(application_id=app.id, to_addr=cand.email if cand else "", type=DraftType.INVITE,
                  subject=f"Next step for the {job.title} position", body=body)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    log_audit(db, actor=actor, action="prepare_invitation", entity="application", entity_id=app.id,
              payload={"draft_id": draft.id, "questions": len(questions)})
    return draft


def find_session(db: Session, token: str) -> VideoSubmission | None:
    """Look up a portal session by token (compares hashes, never stores the raw token)."""
    if not token or len(token) > 200:
        return None
    return db.exec(select(VideoSubmission).where(VideoSubmission.token_hash == hash_token(token))).first()
