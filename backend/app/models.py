"""SQLModel table definitions."""
from datetime import date, datetime
from pydantic import NaiveDatetime  # local time, no timezone (works with all SQLModel versions)
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
    created_at: NaiveDatetime = Field(default_factory=datetime.now)


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
    created_at: NaiveDatetime = Field(default_factory=datetime.now)


class Score(SQLModel, table=True):
    """Scoring result for an application."""
    __tablename__ = "scores"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="applications.id")
    criteria_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    total: float
    model: str
    prompt_version: str
    created_at: NaiveDatetime = Field(default_factory=datetime.now)


class InterviewQuestion(SQLModel, table=True):
    """Interview question for a job."""
    __tablename__ = "interview_questions"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id")
    application_id: Optional[int] = Field(foreign_key="applications.id")
    text: str
    rubric: str
    is_tailored: bool = False
    created_at: NaiveDatetime = Field(default_factory=datetime.now)


class VideoSubmission(SQLModel, table=True):
    """Video/audio submission from candidate."""
    __tablename__ = "video_submissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="applications.id")
    path: str
    token_hash: str  # SHA256 of one-time token
    expires_at: NaiveDatetime
    used: bool = False
    transcript_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: NaiveDatetime = Field(default_factory=datetime.now)


class Evaluation(SQLModel, table=True):
    """Evaluation of interview responses."""
    __tablename__ = "evaluations"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="applications.id")
    per_question_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    recommendation: str  # "Advance" | "Hold" | "Not recommended"
    confidence: float
    summary_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: NaiveDatetime = Field(default_factory=datetime.now)


class Draft(SQLModel, table=True):
    """Draft email awaiting approval."""
    __tablename__ = "drafts"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: Optional[int] = Field(default=None, foreign_key="applications.id")
    email_id: Optional[int] = Field(default=None, foreign_key="emails.id")
    to_addr: str = ""
    type: DraftType
    subject: str
    body: str
    status: DraftStatus = DraftStatus.PENDING
    approved_by: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: NaiveDatetime = Field(default_factory=datetime.now)


class EmailCategory(str, Enum):
    """What kind of email this is."""
    CANDIDATE_APPLICATION = "candidate_application"
    CANDIDATE_REPLY = "candidate_reply"
    WORK_MEETING = "work_meeting"
    WORK_REQUEST = "work_request"
    WORK_INFO = "work_info"
    SPAM_PHISHING = "spam_phishing"


class Urgency(str, Enum):
    """Final urgency decided by the urgency engine (rules in code)."""
    URGENT = "urgent"
    NORMAL = "normal"
    LOW = "low"
    FLAGGED = "flagged"  # phishing or manipulation attempt


class EmailStatus(str, Enum):
    NEW = "new"
    HANDLED = "handled"


class Email(SQLModel, table=True):
    """Incoming email from the HR inbox, with the AI analysis."""
    __tablename__ = "emails"

    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: str = Field(default="", index=True)  # to avoid importing twice
    from_name: str = ""
    from_addr: str
    to_addr: str = ""
    subject: str
    body: str
    attachments_json: list = Field(default_factory=list, sa_column=Column(JSON))
    received_at: NaiveDatetime = Field(default_factory=datetime.now)

    # AI analysis (validated JSON) + final decision by rules
    category: str = "work_info"
    summary: str = ""
    urgency: str = "normal"
    urgency_reasons_json: list = Field(default_factory=list, sa_column=Column(JSON))
    needs_human: bool = False
    injection_suspected: bool = False
    injection_text: str = ""
    security_flags_json: list = Field(default_factory=list, sa_column=Column(JSON))
    analysis_source: str = ""  # "ai" or "rules" (offline fallback)
    status: EmailStatus = EmailStatus.NEW
    application_id: Optional[int] = Field(default=None, foreign_key="applications.id")


class EventType(str, Enum):
    MEETING = "meeting"
    DEADLINE = "deadline"


class EventStatus(str, Enum):
    SUGGESTED = "suggested"   # found by AI, waiting for HR
    CONFIRMED = "confirmed"   # HR clicked confirm
    DISMISSED = "dismissed"   # HR clicked dismiss


class Event(SQLModel, table=True):
    """Meeting or deadline found in an email. HR confirms or dismisses it."""
    __tablename__ = "events"

    id: Optional[int] = Field(default=None, primary_key=True)
    email_id: int = Field(foreign_key="emails.id")
    type: EventType
    title: str
    date: Optional[str] = None   # YYYY-MM-DD
    time: Optional[str] = None   # HH:MM
    location: str = ""
    attendees_json: list = Field(default_factory=list, sa_column=Column(JSON))
    status: EventStatus = EventStatus.SUGGESTED
    decided_by: Optional[str] = None
    created_at: NaiveDatetime = Field(default_factory=datetime.now)


class Decision(SQLModel, table=True):
    """Final HUMAN decision about a candidate (the AI only recommends)."""
    __tablename__ = "decisions"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="applications.id", index=True)
    decision: str            # "advance" | "reject"
    ai_recommendation: str   # what the AI recommended at that moment
    agrees_with_ai: bool
    note: str = ""           # required when HR disagrees with the AI
    decided_by: str          # "user:<id>"
    created_at: NaiveDatetime = Field(default_factory=datetime.now)


class OfferStatus(str, Enum):
    DRAFT = "draft"          # email with the slots is waiting for HR approval
    PENDING = "pending"      # sent: candidate can pick a slot (slots are held)
    BOOKED = "booked"
    DECLINED = "declined"    # candidate said none of the slots work
    EXPIRED = "expired"      # nobody answered in time: slots released
    CANCELLED = "cancelled"


class ScheduleOffer(SQLModel, table=True):
    """A set of 3 interview slots proposed to one candidate, answered through a one-time link."""
    __tablename__ = "schedule_offers"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="applications.id", index=True)
    draft_id: Optional[int] = Field(default=None, foreign_key="drafts.id")
    token_hash: str = Field(index=True)
    status: OfferStatus = OfferStatus.DRAFT
    round: int = 1
    availability_note: str = ""   # what the candidate wrote when declining
    expires_at: NaiveDatetime
    created_at: NaiveDatetime = Field(default_factory=datetime.now)


class SlotStatus(str, Enum):
    HELD = "held"            # reserved while the candidate decides
    BOOKED = "booked"
    RELEASED = "released"


class InterviewSlot(SQLModel, table=True):
    """One proposed interview time. Held and booked slots block HR's calendar."""
    __tablename__ = "interview_slots"

    id: Optional[int] = Field(default=None, primary_key=True)
    offer_id: int = Field(foreign_key="schedule_offers.id", index=True)
    application_id: int = Field(foreign_key="applications.id", index=True)
    start: NaiveDatetime
    end: NaiveDatetime
    status: SlotStatus = SlotStatus.HELD


class TimeRequest(SQLModel, table=True):
    """A candidate wrote an email proposing an interview time. HR books it or proposes alternatives."""
    __tablename__ = "time_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="applications.id", index=True)
    email_id: int = Field(foreign_key="emails.id")
    requested_start: Optional[NaiveDatetime] = None   # None if only a day / period was given
    text: str = ""
    status: str = "open"   # open | booked | answered | dismissed
    created_at: NaiveDatetime = Field(default_factory=datetime.now)


class UserSession(SQLModel, table=True):
    """Server-side login session. The browser only holds a random token (HttpOnly cookie);
    we store its SHA-256 hash, so a database leak does not leak usable sessions."""
    __tablename__ = "sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    token_hash: str = Field(index=True, unique=True)
    csrf_token: str
    user_id: int = Field(foreign_key="users.id")
    expires_at: NaiveDatetime
    created_at: NaiveDatetime = Field(default_factory=datetime.now)


class AuditLog(SQLModel, table=True):
    """Append-only audit log."""
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    actor: str  # "ai" | "system" | "user:<id>"
    action: str
    entity: str
    entity_id: int
    payload_hash: str
    timestamp: NaiveDatetime = Field(default_factory=datetime.now)


class SentEmail(SQLModel, table=True):
    """When each approved email actually left HR Buddy (used to know how long we have been waiting)."""
    __tablename__ = "sent_emails"

    id: Optional[int] = Field(default=None, primary_key=True)
    draft_id: int = Field(foreign_key="drafts.id", index=True)
    application_id: Optional[int] = Field(default=None, foreign_key="applications.id", index=True)
    kind: str = "other"   # invite | answers_reminder | schedule | schedule_reminder | closing | other
    sent_at: NaiveDatetime = Field(default_factory=datetime.now)


class Employee(SQLModel, table=True):
    """A (fictional) employee of the company. Only what HR needs for leave: no health data."""
    __tablename__ = "employees"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(index=True, unique=True)
    team: str = Field(index=True)
    title: str = ""


class LeaveType(str, Enum):
    ANNUAL = "annual"   # paid leave, counted against the yearly allowance
    SICK = "sick"       # only the word "sick" is stored, never an illness


class LeaveStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROPOSED = "proposed"   # HR proposed other dates


class LeaveRequest(SQLModel, table=True):
    """A leave request (from an email or entered by HR). Only a human approves or rejects it."""
    __tablename__ = "leave_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    type: LeaveType = LeaveType.ANNUAL
    start: date
    end: date
    status: LeaveStatus = LeaveStatus.PENDING
    email_id: Optional[int] = Field(default=None, foreign_key="emails.id")
    reason_from_employee: str = ""   # short, what they wrote (no medical details are asked)
    hr_note: str = ""
    extracted_by: str = "rules"      # "ai" or "rules"
    decided_by: str = ""
    created_at: NaiveDatetime = Field(default_factory=datetime.now)


class JobPost(SQLModel, table=True):
    """The public job post of a Job: HR's key facts, the AI draft, checks, and publication (human only)."""
    __tablename__ = "job_posts"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id", index=True, unique=True)
    code: str = Field(index=True)                 # e.g. JOB-002, used in the application email subject
    details_json: dict = Field(default_factory=dict, sa_column=Column(JSON))   # what HR entered
    text: str = ""                                # the post (AI draft, then edited by HR)
    generated_by: str = "template"                # "ai" | "template"
    checks_json: dict = Field(default_factory=dict, sa_column=Column(JSON))    # fairness + fact checks
    status: str = "draft"                         # draft | published | closed
    public_slug: str = Field(default="", index=True)
    published_by: Optional[int] = None
    published_at: Optional[NaiveDatetime] = None
    created_at: NaiveDatetime = Field(default_factory=datetime.now)
