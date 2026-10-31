"""SQLModel table definitions."""
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column, DateTime


class UserRole(str, Enum):
    """User roles."""
    RECRUITER = "recruiter"
    ADMIN = "admin"


class ApplicationStatus(str, Enum):
    """Candidate application status."""
    RECEIVED = "RECEIVED"
    QUARANTINED = "QUARANTINED"
    SCREENED = "SCREENED"
    SCORED = "SCORED"
    SHORTLISTED = "SHORTLISTED"
    INVITED = "INVITED"
    VIDEO_SUBMITTED = "VIDEO_SUBMITTED"
    EVALUATED = "EVALUATED"
    DECIDED = "DECIDED"


class DraftType(str, Enum):
    """Draft email types."""
    INVITE = "invite"
    REPLY = "reply"
    REMINDER = "reminder"
    REJECTION = "rejection"


class DraftStatus(str, Enum):
    """Draft approval statuses."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"


class User(SQLModel, table=True):
    """User (recruiter or admin)."""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    role: UserRole = UserRole.RECRUITER


class Job(SQLModel, table=True):
    """Job posting."""
    __tablename__ = "jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    rubric_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    rubric_approved_by: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Candidate(SQLModel, table=True):
    """Candidate identity."""
    __tablename__ = "candidates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)


class Application(SQLModel, table=True):
    """Job application with anonymized profile."""
    __tablename__ = "applications"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id")
    candidate_id: int = Field(foreign_key="candidates.id")
    cv_path: Optional[str] = None
    status: ApplicationStatus = ApplicationStatus.RECEIVED
    security_flags_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    anonymized_profile_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Score(SQLModel, table=True):
    """Scoring result for an application."""
    __tablename__ = "scores"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="applications.id")
    criteria_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    total: float
    model: str
    prompt_version: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InterviewQuestion(SQLModel, table=True):
    """Interview question for a job."""
    __tablename__ = "interview_questions"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id")
    application_id: Optional[int] = Field(foreign_key="applications.id")
    text: str
    rubric: str
    is_tailored: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VideoSubmission(SQLModel, table=True):
    """Video/audio submission from candidate."""
    __tablename__ = "video_submissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="applications.id")
    path: str
    token_hash: str  # SHA256 of one-time token
    expires_at: datetime
    used: bool = False
    transcript_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Evaluation(SQLModel, table=True):
    """Evaluation of interview responses."""
    __tablename__ = "evaluations"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="applications.id")
    per_question_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    recommendation: str  # "Advance" | "Hold" | "Not recommended"
    confidence: float
    summary_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Draft(SQLModel, table=True):
    """Draft email awaiting approval."""
    __tablename__ = "drafts"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: Optional[int] = Field(foreign_key="applications.id")
    type: DraftType
    subject: str
    body: str
    status: DraftStatus = DraftStatus.PENDING
    approved_by: Optional[int] = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Email(SQLModel, table=True):
    """Incoming email from HR inbox."""
    __tablename__ = "emails"

    id: Optional[int] = Field(default=None, primary_key=True)
    from_addr: str
    subject: str
    body: str
    category: str  # "application" | "inquiry" | "follow-up" | "spam"
    urgency: str  # "high" | "normal" | "low"
    needs_human: bool = False
    injection_suspected: bool = False
    received_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(SQLModel, table=True):
    """Append-only audit log."""
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    actor: str  # "ai" | "system" | "user:<id>"
    action: str
    entity: str
    entity_id: int
    payload_hash: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
