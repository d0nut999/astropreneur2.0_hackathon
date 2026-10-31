"""Draft replies. A draft is NEVER sent automatically: it goes to the approval queue."""
from pathlib import Path

from sqlmodel import Session

from ..llm import LLMError, complete_json
from ..models import Email
from ..schemas import DraftReply

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "draft_reply.md"


def draft_reply(email: Email, db: Session | None = None) -> tuple[DraftReply, str]:
    """Return (draft, source) where source is "ai" or "template"."""
    user = (
        f"<original_email>\nFrom: {email.from_name} <{email.from_addr}>\n"
        f"Subject: {email.subject}\n\n{email.body[:4000]}\n</original_email>\n\n"
        f"Short summary of what they want: {email.summary}"
    )
    try:
        draft = complete_json(task="draft_reply", system=PROMPT_PATH.read_text(encoding="utf-8"),
                              user=user, schema=DraftReply, prompt_version="draft_v1", db=db)
        return draft, "ai"
    except LLMError:
        name = (email.from_name or "").split(" ")[0] or "there"
        subject = email.subject if email.subject.lower().startswith("re:") else f"Re: {email.subject}"
        body = (f"Hello {name},\n\nThank you for your message. We have received it and will get back "
                f"to you shortly.\n\nBest regards,\nHR Team")
        return DraftReply(subject=subject, body=body), "template"
