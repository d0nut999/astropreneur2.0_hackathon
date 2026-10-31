# HireGuard: Complete Project Structure & Task Guide

**A secure AI recruiting assistant with mandatory human oversight.** This document describes the current codebase and how to divide work among team members.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Folder Structure](#folder-structure)
4. [How Things Work](#how-things-work)
5. [Task Breakdown](#task-breakdown)
6. [How to Get Started](#how-to-get-started)
7. [Running & Testing](#running--testing)
8. [Common Patterns](#common-patterns)

---

## Project Overview

**HireGuard** is a full-stack web application that:

1. **Receives applications** (email with CV attachment)
2. **Screens CVs** (security gate: detects hidden text, prompt injection)
3. **Scores candidates** (anonymized profile, LLM scoring against job rubric)
4. **Conducts interviews** (one-time portal link, video/audio submission, transcription)
5. **Evaluates responses** (LLM evaluation against rubric)
6. **Recommends** (Advance / Hold / Not Recommended)
7. **Drafts emails** (all drafts go to approval queue first)

**Golden Rule: "The agent executes, the human decides."** Every human-level decision requires an HR click. AI cannot directly change candidate status or send emails.

---

## Architecture

### Three-Layer Design

```
Frontend (React + Tailwind)
    ↓
API Client (mock mode for testing)
    ↓
Backend API (FastAPI)
    ↓
Services (business logic stubs)
    ↓
Database (SQLite)
```

### State Machine (Human-in-the-Loop)

```
RECEIVED
    ↓
SCREENED or QUARANTINED (AI decides based on security checks)
    ↓
SCORED (AI scores, human sees results)
    ↓
SHORTLISTED* (HUMAN ONLY - must click to shortlist)
    ↓
INVITED* (HUMAN ONLY - must approve email before sending)
    ↓
VIDEO_SUBMITTED (candidate submits video/audio)
    ↓
EVALUATED (AI evaluates video, human sees recommendation)
    ↓
DECIDED* (HUMAN ONLY - makes final yes/no decision)
```

`*` = Only humans can enter. AI attempting to force these states raises `StateTransitionError`.

### Key Design Principle

**"The reader can't act, the actor can't read."**
- LLM reads untrusted content (CVs, emails, transcripts) → returns JSON only
- Normal Python code receives JSON → makes decisions (status changes, sending emails)
- All decisions that affect people require human approval via UI

---

## Folder Structure

```
hackathon/
├── backend/                          # Python FastAPI backend
│   ├── app/                          # Main application code
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app factory, middleware, router registration
│   │   ├── config.py                 # Settings loaded from .env
│   │   ├── db.py                     # SQLite engine, session dependency, init_db()
│   │   ├── models.py                 # SQLModel table definitions + enums
│   │   ├── schemas.py                # Pydantic request/response + LLM task schemas
│   │   ├── auth.py                   # Password hashing, session handling
│   │   ├── audit.py                  # Append-only audit logging helper
│   │   ├── state_machine.py          # State transitions with HITL enforcement (TESTED)
│   │   ├── llm.py                    # LLM wrapper (caching, validation, fallbacks)
│   │   ├── security_headers.py       # CSP, X-Frame-Options, X-Content-Type-Options
│   │   │
│   │   ├── routes/                   # API endpoint files (auto-registered)
│   │   │   ├── __init__.py
│   │   │   ├── health.py             # GET /health
│   │   │   ├── auth.py               # POST /auth/login, /auth/logout, GET /auth/me
│   │   │   ├── jobs.py               # GET/POST /jobs, POST /jobs/{id}/rubric/approve
│   │   │   ├── candidates.py         # GET /candidates, GET /candidates/{id}, POST /shortlist, /decision
│   │   │   ├── approvals.py          # GET /approvals, POST /approve, /reject
│   │   │   ├── digest.py             # GET /digest/today
│   │   │   ├── audit.py              # GET /audit (append-only log)
│   │   │   └── portal.py             # GET/POST /portal/{token} (public, candidate-facing)
│   │   │
│   │   ├── services/                 # Business logic stubs (YOU FILL THESE IN)
│   │   │   ├── __init__.py
│   │   │   ├── security_gate.py      # check_upload(), find_hidden_text() → validate files
│   │   │   ├── parser.py             # parse_cv() → extract text from PDF/DOCX
│   │   │   ├── anonymizer.py         # anonymize_profile() → remove PII
│   │   │   ├── scorer.py             # score_candidate() → LLM scoring
│   │   │   ├── evaluator.py          # evaluate_interview() → LLM eval of responses
│   │   │   ├── transcriber.py        # transcribe_video() → audio to text
│   │   │   ├── mailer.py             # send_email() → SMTP
│   │   │   └── digest.py             # generate_digest() → daily summary
│   │   │
│   │   └── prompts/                  # LLM prompts (you'll add these)
│   │       ├── extract.md            # Extract info from CV
│   │       ├── score.md              # Score candidate
│   │       ├── questions.md          # Generate questions
│   │       ├── evaluate.md           # Evaluate interview
│   │       └── injection_check.md    # Detect prompt injection
│   │
│   ├── scripts/
│   │   ├── __init__.py
│   │   └── seed.py                   # Create demo data (run this first!)
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_health.py            # Test /health endpoint
│   │   ├── test_hitl.py              # Test that AI cannot enter human-only states (IMPORTANT)
│   │   ├── test_upload.py            # Placeholder for upload tests
│   │   └── test_injection.py         # Placeholder for injection detection tests
│   │
│   ├── data/                         # Created at runtime (gitignored)
│   │   ├── hireguard.db              # SQLite database file
│   │   ├── uploads/                  # Uploaded CVs, videos
│   │   └── llm_cache/                # Cached LLM responses
│   │
│   ├── .env                          # Environment variables (gitignored, copy from .env.example)
│   ├── .env.example                  # Template for .env
│   ├── requirements.txt               # Python dependencies
│   ├── Dockerfile                    # Docker image for backend
│   └── .gitignore
│
├── frontend/                         # React + Vite frontend
│   ├── src/
│   │   ├── api/                      # API communication layer
│   │   │   ├── client.js             # Axios wrapper (base URL, credentials)
│   │   │   ├── mock.js               # Hardcoded mock responses for testing without backend
│   │   │   └── index.js              # Entry point (switches real/mock based on VITE_USE_MOCK)
│   │   │
│   │   ├── components/               # Shared UI components
│   │   │   ├── Layout.jsx            # Header, nav, footer (wraps all pages)
│   │   │   ├── StatusBadge.jsx       # Colored status labels (RECEIVED, SCREENED, etc.)
│   │   │   ├── EvidenceQuote.jsx     # Display quoted evidence from LLM (plain text only)
│   │   │   └── FlagBanner.jsx        # Security flag alerts
│   │   │
│   │   ├── pages/                    # Full pages (one per route)
│   │   │   ├── Login.jsx             # /login - authentication
│   │   │   ├── Dashboard.jsx         # / or /dashboard - overview + digest
│   │   │   ├── Jobs.jsx              # /jobs - job listing
│   │   │   ├── Candidates.jsx        # /candidates/{id} - full profile (scores, flags, eval)
│   │   │   ├── Approvals.jsx         # /approvals - draft email queue
│   │   │   ├── Audit.jsx             # /audit - append-only log viewer
│   │   │   └── Portal.jsx            # /portal/{token} - candidate interview portal (public)
│   │   │
│   │   ├── App.jsx                   # Main router (BrowserRouter, Routes)
│   │   ├── main.jsx                  # React entry point
│   │   └── index.css                 # Tailwind CSS import
│   │
│   ├── index.html                    # HTML template
│   ├── vite.config.js                # Vite build config
│   ├── tailwind.config.js            # Tailwind CSS config
│   ├── postcss.config.js             # PostCSS config (for Tailwind)
│   ├── package.json                  # Node dependencies
│   ├── .gitignore
│   └── node_modules/                 # Created by npm install
│
├── docker-compose.yml                # Docker services (backend, frontend, Mailpit)
├── .gitignore                        # Git ignore rules
├── README.md                         # Full documentation
├── QUICKSTART.md                     # 10-minute setup guide
├── TEAM_GUIDE.md                     # This file - task breakdown for team
└── Changes.md                        # Original spec (reference)
```

---

## How Things Work

### 1. Frontend → API → Backend Flow

```
User clicks "Upload CV"
    ↓
React form sends file to POST /candidates/{id}/upload_cv
    ↓
Backend receives file, saves to data/uploads/
    ↓
Calls app.services.security_gate.check_upload()
    ↓
Returns GateResult (is_safe, flags, confidence)
    ↓
Backend updates Application status (SCREENED or QUARANTINED)
    ↓
Frontend fetches candidate detail, shows flags if any
```

### 2. State Transitions (Enforced)

```python
# In backend/app/state_machine.py
from app.state_machine import transition

# When HR clicks "Shortlist" button:
transition(
    db=session,
    application=app_obj,
    to_state=ApplicationStatus.SHORTLISTED,
    actor="user:123"  # user ID from session
)
# ✅ Works - human can enter SHORTLISTED

# If AI tries to do it:
transition(
    db=session,
    application=app_obj,
    to_state=ApplicationStatus.SHORTLISTED,
    actor="ai"
)
# ❌ Raises StateTransitionError: "Only humans may transition to SHORTLISTED"
```

### 3. LLM Calls (All Routed Through One Function)

```python
# In backend/app/llm.py
from app.llm import complete_json
from app.schemas import ScoringResult

result = complete_json(
    task="score",
    system="You are an expert recruiter scoring candidates...",
    user=f"Score this candidate:\n{anonymized_profile}",
    schema=ScoringResult,  # Pydantic model
    prompt_version="v1",
    db=session
)

# Features:
# - Validates output against schema
# - Caches result to disk
# - Retries once if invalid JSON
# - Audits the call
# - Uses LLM_FALLBACK_MODELS if set
# - Fails gracefully if LLM_API_KEY is empty
```

### 4. Approval Queue (All Emails Wait Here)

```
Draft email created (status=PENDING):
  - Subject: "You're invited to interview"
  - Body: "Dear Alice, we are pleased to invite you..."

↓

HR sees it in GET /approvals

↓

HR clicks "Approve" → POST /approvals/{draft_id}/approve

↓

Backend updates Draft status to APPROVED, queues for sending

↓

Mailer sends via SMTP

↓

Application status updated to INVITED
```

**No email is ever sent by AI directly. All go through this queue.**

### 5. Audit Log (Append-Only)

Every action creates a record in `audit_logs`:

```sql
id | actor      | action     | entity        | entity_id | payload_hash | timestamp
---|------------|------------|---------------|-----------|--------------|----------
1  | user:1     | login      | user          | 1         | abc123...    | 2024-01-15 10:00:00
2  | ai         | transition | application   | 5         | def456...    | 2024-01-15 10:05:00
3  | user:1     | approve    | draft         | 2         | ghi789...    | 2024-01-15 10:07:00
```

**No deletes. No updates. Full traceability.**

---

## Task Breakdown

### **Task 1: Security Gate (File Upload & Validation)**

**Assign to:** Backend developer (1 person)

**Files to edit:**
- `backend/app/services/security_gate.py` (implement stubs)
- `backend/app/routes/candidates.py` (add upload endpoint)
- `frontend/src/pages/Candidates.jsx` (add upload form)

**What to build:**

```python
# backend/app/services/security_gate.py

def check_upload(file_path: Path) -> GateResult:
    """
    Validate uploaded file:
    - Check file type (only PDF, DOCX)
    - Scan for hidden metadata, comments
    - Check for prompt injection patterns
    - Return GateResult(is_safe, flags, confidence)
    """
    # TODO: Implement using:
    # - python-magic: detect file type
    # - PyMuPDF: read PDF metadata
    # - python-docx: read DOCX metadata
    # - rapidfuzz: fuzzy match injection patterns

def find_hidden_text(file_path: Path) -> list[str]:
    """Find hidden text in PDF/DOCX (comments, metadata)."""
    # TODO: Use PyMuPDF, python-docx to extract metadata
```

**Expected output:**
- `/candidates/{id}/upload_cv` endpoint that:
  1. Receives file upload
  2. Saves to `backend/data/uploads/`
  3. Calls `security_gate.check_upload()`
  4. Updates Application with `security_flags_json`
  5. Sets status to SCREENED (if safe) or QUARANTINED (if flags)

**Test with:**
```bash
curl -X POST http://localhost:8000/candidates/1/upload_cv \
  -F "file=@test.pdf"
```

---

### **Task 2: CV Parsing & Anonymization**

**Assign to:** Backend developer (1 person)

**Files to edit:**
- `backend/app/services/parser.py` (implement stubs)
- `backend/app/services/anonymizer.py` (implement stubs)
- `backend/app/routes/candidates.py` (add parse endpoint)

**What to build:**

```python
# backend/app/services/parser.py

def parse_cv(file_path: str) -> dict:
    """
    Extract structured info from CV:
    - Full text
    - Experience (list of jobs)
    - Education (schools, degrees)
    - Skills (list of skills)
    - Contact info (name, email, phone)
    
    Return as JSON-serializable dict.
    """
    # TODO: Use pdfplumber for PDFs, python-docx for DOCX
    # Extract text, parse into sections

# backend/app/services/anonymizer.py

def anonymize_profile(parsed_cv: dict) -> dict:
    """
    Remove PII from parsed CV:
    - Strip name, email, phone
    - Keep experience years, education, skills
    - Keep job descriptions
    
    Return anonymized profile for LLM scoring.
    """
    # TODO: Remove identifying info
```

**Expected output:**
- `/candidates/{id}/parse_cv` endpoint that:
  1. Reads CV file from `security_gate` output
  2. Calls `parser.parse_cv()` → `anonymizer.anonymize_profile()`
  3. Stores in Application.`anonymized_profile_json`
  4. Returns anonymized profile for display

**The profile should look like:**
```json
{
  "experience_years": 5,
  "education": "Bachelor's in Computer Science, 2019",
  "key_skills": ["Python", "FastAPI", "SQL", "Docker"],
  "recent_experience": "5 years as backend engineer at tech company..."
}
```

---

### **Task 3: Candidate Scoring**

**Assign to:** Backend developer + LLM integration (1-2 people)

**Files to edit:**
- `backend/app/services/scorer.py` (implement stubs)
- `backend/app/routes/candidates.py` (add score endpoint)
- `backend/app/prompts/score.md` (write LLM prompt)
- `frontend/src/pages/Candidates.jsx` (display scores + evidence)

**What to build:**

```python
# backend/app/services/scorer.py

def score_candidate(anonymized_profile: dict, rubric: dict) -> dict:
    """
    Score candidate against job rubric using LLM:
    - Get anonymized profile + rubric
    - Call LLM to score each criterion
    - Return per-criterion scores with evidence quotes
    """
    from app.llm import complete_json
    from app.schemas import ScoringResult
    
    # TODO: Build prompt, call LLM, return ScoringResult
```

**Expected output:**
- `/candidates/{id}/score` endpoint that:
  1. Gets anonymized profile + job rubric
  2. Calls `scorer.score_candidate()`
  3. Stores Score record with criteria + total
  4. Updates Application status to SCORED
  5. Returns scores to frontend

**Scores should look like:**
```json
{
  "per_criterion": {
    "experience": 8,
    "technical_skills": 9,
    "communication": 6
  },
  "total": 7.7,
  "evidence_quotes": {
    "experience": "5 years as backend engineer...",
    "technical_skills": "Proficient in Python, FastAPI, Docker..."
  }
}
```

---

### **Task 4: Interview Questions & Transcription**

**Assign to:** Backend developer + audio/ML (1-2 people)

**Files to edit:**
- `backend/app/services/transcriber.py` (implement stubs)
- `backend/app/routes/portal.py` (implement video submission)
- `backend/app/prompts/questions.md` (write LLM prompt)
- `frontend/src/pages/Portal.jsx` (add video upload)

**What to build:**

```python
# backend/app/services/transcriber.py

def transcribe_video(file_path: str) -> str:
    """
    Convert audio/video to text using faster-whisper.
    Note: Import lazily so model doesn't download at startup.
    """
    # TODO: Use faster-whisper
    # from faster_whisper import WhisperModel
    # model = WhisperModel("base", device="cpu")
```

**Expected output:**
- `/portal/{token}/video` endpoint that:
  1. Receives video/audio file upload
  2. Verifies token is valid + not expired
  3. Calls `transcriber.transcribe_video()`
  4. Stores transcript in VideoSubmission
  5. Updates Application status to VIDEO_SUBMITTED

**Portal link format:**
```
http://localhost:5173/portal/abc123xyz789
```

Token is one-time use, expires after 72 hours (configurable).

---

### **Task 5: Interview Evaluation**

**Assign to:** Backend developer + LLM integration (1-2 people)

**Files to edit:**
- `backend/app/services/evaluator.py` (implement stubs)
- `backend/app/routes/candidates.py` (add evaluate endpoint)
- `backend/app/prompts/evaluate.md` (write LLM prompt)
- `frontend/src/pages/Candidates.jsx` (display recommendation)

**What to build:**

```python
# backend/app/services/evaluator.py

def evaluate_interview(transcript: str, questions: list[dict], rubric: dict) -> dict:
    """
    Evaluate interview responses using LLM:
    - Get transcript (from transcriber)
    - Get questions + rubric
    - Call LLM to evaluate each response
    - Return recommendation: "Advance" | "Hold" | "Not Recommended"
    """
    # TODO: Call LLM with transcript + questions
```

**Expected output:**
- `/candidates/{id}/evaluate` endpoint that:
  1. Gets transcript + questions + rubric
  2. Calls `evaluator.evaluate_interview()`
  3. Stores Evaluation record
  4. Updates Application status to EVALUATED
  5. Returns recommendation to frontend

**Recommendation should look like:**
```json
{
  "per_question": {
    "q1": { "score": 8, "notes": "Strong problem-solving..." },
    "q2": { "score": 7, "notes": "Good communication..." }
  },
  "recommendation": "Advance",
  "confidence": 0.85,
  "summary": "Strong technical candidate with good communication skills..."
}
```

---

### **Task 6: Email Drafting & Sending**

**Assign to:** Backend developer (1 person)

**Files to edit:**
- `backend/app/services/mailer.py` (implement stubs)
- `backend/app/routes/candidates.py` (add draft endpoint)
- `backend/app/prompts/draft.md` (write LLM prompt for email generation)
- `frontend/src/pages/Approvals.jsx` (approve/reject drafts)

**What to build:**

```python
# backend/app/services/mailer.py

def send_email(to: str, subject: str, body: str) -> bool:
    """Send email via SMTP (configured for Mailpit in dev)."""
    # TODO: Use smtplib to send via SMTP_HOST:SMTP_PORT
    # Email goes to Mailpit inbox (view at http://localhost:8025)
```

**Expected output:**
- `/candidates/{id}/draft_invite` endpoint that:
  1. Gets candidate info + job info
  2. Calls LLM to draft email (using prompt)
  3. Creates Draft record with status=PENDING
  4. Returns draft to frontend for HR review
- `/approvals/{draft_id}/approve` endpoint that:
  1. HR clicks approve
  2. Calls `mailer.send_email()`
  3. Updates Draft status to SENT
  4. Updates Application status to INVITED
  5. Creates AuditLog entry

---

### **Task 7: Dashboard & Frontend UI**

**Assign to:** Frontend developer (1-2 people)

**Files to edit:**
- `frontend/src/pages/*.jsx` (all pages)
- `frontend/src/components/*.jsx` (shared components)

**What to build:**

- **Dashboard**: Show digest (high-urgency count, pending approvals, pending apps)
- **Jobs**: List jobs, click to view candidates ranked by score
- **Candidates**: Full profile with scores, evidence, flags, evaluation, buttons to shortlist/decide
- **Approvals**: List pending drafts, approve/reject buttons
- **Audit**: Table of all actions (actor, action, entity, timestamp)
- **Portal**: Public page with questions, video upload, submit button

**Key rules:**
- All CV/LLM/email text rendered as **plain text only** (no HTML)
- All state changes go through buttons (never direct API calls)
- Status updates use color-coded StatusBadge components
- Evidence quotes use EvidenceQuote component (with border + formatting)

---

### **Task 8: Testing & Quality Assurance**

**Assign to:** QA / any developer (1 person)

**Files to edit:**
- `backend/tests/test_*.py` (write real tests)

**What to test:**

```python
# backend/tests/test_security_gate.py
def test_safe_pdf():
    """Test that clean PDF passes security check."""
    result = security_gate.check_upload("test.pdf")
    assert result.is_safe == True
    assert result.flags == []

def test_injection_detected():
    """Test that prompt injection is detected."""
    result = security_gate.check_upload("malicious.pdf")
    assert result.is_safe == False
    assert "prompt_injection" in result.flags

# backend/tests/test_state_machine.py (already written for HITL)
def test_ai_cannot_shortlist():
    """Prove AI actor cannot enter SHORTLISTED state."""
    with pytest.raises(StateTransitionError):
        transition(db, app, SHORTLISTED, actor="ai")
```

Run tests:
```bash
cd backend
pytest tests/ -v
```

---

## How to Get Started

### 1. Clone & Install (5 minutes)

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### 2. Start Services (3 minutes)

```bash
# From project root
docker-compose up
```

Waits for:
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- Mailpit: http://localhost:8025

### 3. Seed Database (1 minute)

```bash
python backend/scripts/seed.py
```

Creates:
- Admin: admin@fictional-company.test / admin123
- Recruiter: recruiter@fictional-company.test / recruiter123
- 1 demo job
- 3 demo candidates

### 4. Open Frontend

Visit http://localhost:5173, login with recruiter creds.

---

## Running & Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest tests/

# Run specific test
pytest tests/test_hitl.py::test_ai_cannot_shortlist -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Frontend in Mock Mode

```bash
# In docker-compose.yml or .env:
VITE_USE_MOCK=true

# All pages work without backend running
# Uses hardcoded mock data from frontend/src/api/mock.js
```

### API Documentation

Visit http://localhost:8000/docs (auto-generated Swagger UI)

---

## Common Patterns

### Adding a New Service

```python
# 1. Create file: backend/app/services/my_feature.py

def my_function(input_data: dict) -> dict:
    """Docstring describing what this does."""
    # TODO: Implement
    return {"result": "TODO"}

# 2. Add Pydantic schema in backend/app/schemas.py

class MyResult(BaseModel):
    result: str

# 3. Create route in backend/app/routes/my_feature.py

@router.post("/my_endpoint")
async def call_my_feature(req: MyRequest, db: Session = Depends(get_session)):
    """Endpoint description."""
    result = services.my_feature.my_function(req.model_dump())
    # Update database, call state_machine, audit log, etc.
    return result

# 4. It's auto-registered in backend/app/main.py
# No manual imports needed!
```

### Calling the LLM

```python
from app.llm import complete_json
from app.schemas import SomeResult

result = complete_json(
    task="my_task",
    system="You are an expert recruiter...",
    user=f"Here's the candidate:\n{profile}",
    schema=SomeResult,  # Pydantic model for validation
    prompt_version="v1",
    db=session
)

# result is an instance of SomeResult
print(result.field_name)
```

### Recording State Changes

```python
from app.state_machine import transition

# Any time status changes, use this function:
transition(
    db=session,
    application=app_obj,
    to_state=ApplicationStatus.SCORED,
    actor="ai"  # or "user:123", "system"
)

# Creates AuditLog entry automatically
# Enforces HITL rules
# Raises StateTransitionError if invalid
```

### Making API Calls from Frontend

```javascript
// Use the api module (switches real/mock)
import { apiGet, apiPost } from '../api'

// Get data
const res = await apiGet('/candidates/1')
console.log(res.data)

// Post data
const res = await apiPost('/candidates/1/shortlist', {})
console.log(res.data)

// Mock mode: set VITE_USE_MOCK=true in env
// All calls return hardcoded mock data (useful for testing UI without backend)
```

### Rendering LLM Content (Plain Text Only)

```javascript
// CORRECT - plain text only
<div>{evidence.quote}</div>
<pre>{transcript}</pre>
<p>{emailBody}</p>

// WRONG - never use dangerouslySetInnerHTML for LLM content
<div dangerouslySetInnerHTML={{__html: evidence.quote}} />
// This is a security risk!
```

---

## Environment Variables

**Backend (.env file - copy from .env.example):**

```env
# App
APP_ENV=dev
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./data/hireguard.db

# CORS
CORS_ORIGINS=http://localhost:5173

# LLM (leave empty initially, backend won't crash)
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=
LLM_MODEL=meta-llama/llama-2-7b-chat
LLM_FALLBACK_MODELS=
LLM_TEMPERATURE=0
LLM_CACHE_ENABLED=true
LLM_MAX_ATTEMPTS=2

# Email (Mailpit for dev)
SMTP_HOST=mailpit
SMTP_PORT=1025
IMAP_HOST=mailpit
IMAP_PORT=1143
IMAP_USER=
IMAP_PASSWORD=
HR_MAILBOX=hr@fictional-company.test

# Limits
MAX_UPLOAD_MB=5
MAX_VIDEO_MB=100
PORTAL_TOKEN_TTL_HOURS=72
```

**Frontend (.env for Vite):**

```env
VITE_USE_MOCK=false
VITE_API_URL=http://localhost:8000
```

---

## Database Schema (Read-Only Reference)

```sql
-- Users
users(id, email, password_hash, role)

-- Jobs
jobs(id, title, description, rubric_json, rubric_approved_by, created_at)

-- Candidates & Applications
candidates(id, name, email)
applications(
  id, job_id, candidate_id, cv_path, status,
  security_flags_json, anonymized_profile_json, created_at
)

-- Scoring & Evaluation
scores(id, application_id, criteria_json, total, model, prompt_version, created_at)
interview_questions(id, job_id, application_id, text, rubric, is_tailored)
video_submissions(id, application_id, path, token_hash, expires_at, used, transcript_json)
evaluations(id, application_id, per_question_json, recommendation, confidence, summary_json)

-- Approvals & Email
drafts(id, application_id, type, subject, body, status, approved_by, created_at)
emails(id, from_addr, subject, body, category, urgency, needs_human, injection_suspected, received_at)

-- Audit
audit_logs(id, actor, action, entity, entity_id, payload_hash, timestamp)  # Append-only
```

---

## Important Files to Read First

1. **README.md** - Full architecture & security baseline
2. **QUICKSTART.md** - 10-minute setup
3. **backend/app/state_machine.py** - HITL enforcement logic
4. **backend/app/llm.py** - LLM wrapper
5. **backend/tests/test_hitl.py** - Proof that AI cannot enter human-only states
6. **frontend/src/api/index.js** - API client with mock mode

---

## Key Rules for the Team

1. **Always use state_machine.transition()** for any status change
2. **Always use complete_json()** for any LLM call
3. **Always call audit.log_audit()** after data changes
4. **Never render LLM content as HTML** (use plain text)
5. **Never hardcode PII** (all test data is fictional)
6. **Never send emails directly** (always go through approval queue)
7. **Test with mock mode first** (VITE_USE_MOCK=true)

---

## Debugging Tips

```bash
# Backend logs
docker logs -f hireguard_backend

# Frontend logs
docker logs -f hireguard_frontend

# Database queries
sqlite3 backend/data/hireguard.db "SELECT * FROM applications LIMIT 5;"

# Check what's in audit log
sqlite3 backend/data/hireguard.db "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10;"

# API test
curl http://localhost:8000/docs

# Mailpit inbox
open http://localhost:8025
```

---

## Next Steps

1. **Assign tasks** based on team skills
2. **Pick one task** to start (Security Gate is good first task)
3. **Implement service** in `backend/app/services/`
4. **Test locally** with mock mode
5. **Integrate with frontend** once working
6. **Write tests** in `backend/tests/`
7. **Document as you go**

---

## Questions?

- Check **README.md** for architecture details
- Check **backend/app/main.py** for app structure
- Check **backend/app/routes/*** for endpoint examples
- Run `pytest backend/tests/ -v` to see what's already tested
- Look at **frontend/src/api/mock.js** for example API responses

Good luck! 🚀
