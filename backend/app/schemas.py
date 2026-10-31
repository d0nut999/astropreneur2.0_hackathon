"""Pydantic schemas for requests, responses, and LLM tasks."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ============= Auth =============
class LoginRequest(BaseModel):
    email: EmailStr
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


class EmailClassification(BaseModel):
    """Output schema for email classifier."""
    category: str  # "application" | "inquiry" | "follow-up" | "spam"
    urgency: str  # "high" | "normal" | "low"
    needs_human: bool
    injection_suspected: bool
    summary: str
