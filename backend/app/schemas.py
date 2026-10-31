"""Pydantic schemas for requests, responses, and LLM tasks."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


# ============= Auth =============
class LoginRequest(BaseModel):
    email: str  # plain str: demo addresses use the reserved .test domain
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    role: str


# ============= Job =============
class JobCreate(BaseModel):
    title: str
    description: str


class JobResponse(BaseModel):
    id: int
    title: str
    description: str
    rubric_json: dict
    rubric_approved_by: Optional[int]
    created_at: datetime


class RubricApprove(BaseModel):
    rubric_json: dict


# ============= Candidate & Application =============
class CandidateResponse(BaseModel):
    id: int
    name: str
    email: str


class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    candidate_id: int
    status: str
    security_flags_json: dict
    anonymized_profile_json: dict
    created_at: datetime


class CandidateDetailResponse(BaseModel):
    """Full candidate profile with all scores, evidence, flags, evaluation."""
    candidate: CandidateResponse
    application: ApplicationResponse
    scores: list[dict]
    evaluation: Optional[dict]


class ShortlistRequest(BaseModel):
    pass


class DecisionRequest(BaseModel):
    recommendation: str  # "Advance" | "Hold" | "Not recommended"


# ============= Approval Queue =============
class DraftResponse(BaseModel):
    id: int
    application_id: Optional[int]
    type: str
    subject: str
    body: str
    status: str
    approved_by: Optional[int]
    created_at: datetime


class ApprovalDecisionRequest(BaseModel):
    pass  # approve or reject; decision is the action


# ============= Digest =============
class DigestResponse(BaseModel):
    """Daily summary of emails and pending approvals."""
    high_urgency_count: int
    needs_human_count: int
    pending_approvals_count: int
    pending_applications_count: int
    summary: str


# ============= Audit =============
class AuditLogResponse(BaseModel):
    id: int
    actor: str
    action: str
    entity: str
    entity_id: int
    payload_hash: str
    timestamp: datetime


# ============= Portal (candidate-facing, public) =============
class PortalSessionResponse(BaseModel):
    application_id: int
    questions: list[dict]
    token_remaining_hours: int


class VideoUploadResponse(BaseModel):
    success: bool
    message: str


# ============= LLM Task Schemas =============
class SecurityCheckResult(BaseModel):
    """Output schema for security gate check."""
    is_safe: bool
    flags: list[str]
    confidence: float


class AnonymizedProfile(BaseModel):
    """Output schema for anonymizer."""
    experience_years: int
    education: str
    key_skills: list[str]
    relevant_experience: str


class ScoringResult(BaseModel):
    """Output schema for scorer."""
    criteria: dict
    per_criterion_scores: dict
    total: float
    evidence_quotes: dict


class InterviewEvaluation(BaseModel):
    """Output schema for evaluator."""
    per_question_scores: dict
    recommendation: str  # "Advance" | "Hold" | "Not recommended"
    confidence: float
    summary: str


class MeetingInfo(BaseModel):
    """A meeting found in an email."""
    title: str = ""
    date: Optional[str] = None   # "YYYY-MM-DD"
    time: Optional[str] = None   # "HH:MM" (24h)
    location: str = ""
    with_people: list[str] = []


EMAIL_CATEGORIES = {
    "candidate_application", "candidate_reply", "work_meeting",
    "work_request", "work_info", "spam_phishing",
}


class EmailAnalysis(BaseModel):
    """Output schema for the email classifier (LLM or offline rules)."""
    category: str
    summary: str
    needs_human_reply: bool = False
    urgency_hint: str = "normal"          # the AI's opinion only; rules decide
    meeting: Optional[MeetingInfo] = None
    deadline: Optional[str] = None       # "YYYY-MM-DD"
    deadline_what: str = ""
    injection_suspected: bool = False
    injection_text: str = ""

    @field_validator("category")
    @classmethod
    def _known_category(cls, v: str) -> str:
        v = (v or "").strip().lower()
        return v if v in EMAIL_CATEGORIES else "work_info"

    @field_validator("urgency_hint")
    @classmethod
    def _known_urgency(cls, v: str) -> str:
        v = (v or "").strip().lower()
        return v if v in {"urgent", "normal", "low"} else "normal"

    @field_validator("summary")
    @classmethod
    def _short_summary(cls, v: str) -> str:
        return (v or "").strip()[:400]


class DraftReply(BaseModel):
    """Output schema for an AI-drafted reply."""
    subject: str
    body: str


class CriterionScore(BaseModel):
    score: int = 0
    evidence: str = ""
    reason: str = ""

    @field_validator("score", mode="before")
    @classmethod
    def _clamp(cls, v):
        try:
            return max(0, min(5, int(round(float(v)))))
        except (TypeError, ValueError):
            return 0


class CVScoring(BaseModel):
    """Output schema for the CV scorer (LLM or offline)."""
    criteria: dict[str, CriterionScore]
    summary: str = ""
    strengths: list[str] = []
    gaps: list[str] = []
    injection_suspected: bool = False
    injection_text: str = ""
