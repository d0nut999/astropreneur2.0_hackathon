# HireGuard: Secure AI Recruiting Assistant

An AI-powered recruiting system that screens CVs, scores candidates, and automates interview management **with mandatory human oversight** at critical decision points.

## Golden Rule

**"The agent executes, the human decides about people."** Nothing is sent and no candidate state changes without an HR click. **"The reader can't act, the actor can't read."** The LLM reads untrusted content (CVs, emails, transcripts) and returns JSON only. Sending emails, changing status, and writing records are done by normal code behind human-approved endpoints.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### 1. Start Services

```bash
cp backend/.env.example backend/.env
docker-compose up
```

This starts:
- **Backend** (FastAPI) on http://localhost:8000
- **Frontend** (React) on http://localhost:5173
- **Mailpit** (fake SMTP + inbox UI) on http://localhost:8025

### 2. Seed Database

```bash
python backend/scripts/seed.py
```

Creates admin and recruiter users with demo credentials printed to console.

### 3. Access the App

- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **Mailpit Inbox**: http://localhost:8025

## Tech Stack

| Layer | Tech |
|-------|------|
| **Frontend** | React 18 + Vite + TypeScript + Tailwind CSS |
| **Backend** | FastAPI + SQLModel + SQLite |
| **Database** | SQLite (single file, `./backend/data/hireguard.db`) |
| **LLM** | OpenAI-compatible client (OpenRouter, Groq, Ollama, Gemini) |
| **Auth** | Argon2 password hashing + session cookies (HttpOnly) |
| **File Security** | PyMuPDF, python-magic, pdfplumber (stubs now) |
| **Audio** | faster-whisper (lazy import, stubs now) |
| **Email** | stdlib imaplib/smtplib + Mailpit for dev |
| **Infra** | Docker Compose |

## Architecture

### Backend Structure

```
backend/app/
├── main.py              # FastAPI app factory
├── config.py            # Settings from .env
├── db.py                # SQLite engine & session
├── models.py            # SQLModel tables (User, Job, Candidate, Application, etc.)
├── schemas.py           # Pydantic request/response schemas + LLM task schemas
├── auth.py              # Password hashing, role decorators
├── audit.py             # Audit logging helper
├── state_machine.py     # Application state transitions (HITL enforcement)
├── llm.py               # LLM wrapper (caching, validation, fallbacks)
├── security_headers.py  # CSP, X-Frame-Options, etc.
├── routes/              # Auto-registered endpoint files
│   ├── health.py        # /health
│   ├── auth.py          # /auth/login, /auth/me
│   ├── jobs.py          # /jobs
│   ├── candidates.py    # /candidates, /candidates/{id}/shortlist
│   ├── approvals.py     # /approvals (draft queue)
│   ├── digest.py        # /digest/today
│   ├── audit.py         # /audit (append-only log)
│   └── portal.py        # /portal/{token} (public candidate portal)
└── services/            # Business logic stubs
    ├── security_gate.py   # File validation
    ├── parser.py          # CV parsing
    ├── anonymizer.py      # Remove PII
    ├── scorer.py          # Score candidate
    ├── evaluator.py       # Evaluate interview
    ├── transcriber.py     # Audio→text
    ├── mailer.py          # Send emails
    └── digest.py          # Daily summary
```

### State Machine

```
RECEIVED → SCREENED | QUARANTINED
SCREENED → SCORED
SCORED → SHORTLISTED*
SHORTLISTED* → INVITED*
INVITED* → VIDEO_SUBMITTED
VIDEO_SUBMITTED → EVALUATED
EVALUATED → DECIDED*
```

`*` = Human-only state. AI cannot enter SHORTLISTED, INVITED, or DECIDED. Enforced by `state_machine.transition()`. **Attempting to violate this raises StateTransitionError.**

### Frontend Structure

```
frontend/src/
├── api/
│   ├── client.js        # Axios wrapper
│   ├── mock.js          # Mock responses for VITE_USE_MOCK=true
│   └── index.js         # Entry point (switches real/mock)
├── components/
│   ├── Layout.jsx       # Header, nav, footer
│   ├── StatusBadge.jsx  # Color-coded status labels
│   ├── EvidenceQuote.jsx# Evidence display (plain text only)
│   └── FlagBanner.jsx   # Security flag alerts
├── pages/
│   ├── Dashboard.jsx    # Main overview + digest
│   ├── Login.jsx        # Auth page
│   ├── Jobs.jsx         # Job listing
│   ├── Portal.jsx       # Candidate portal (public)
│   ├── Approvals.jsx    # Draft approval queue
│   └── Audit.jsx        # Audit log viewer
├── App.jsx              # Routes
└── main.jsx, index.css
```

**Mock Mode**: Set `VITE_USE_MOCK=true` in `.env` to test frontend without backend. All pages work with hardcoded mock data.

## API Endpoints

### Authentication
- `POST /auth/login` — Login
- `POST /auth/logout` — Logout
- `GET /auth/me` — Current user

### Jobs
- `GET /jobs` — List jobs
- `POST /jobs` — Create job (admin)
- `POST /jobs/{id}/rubric/approve` — Approve rubric (human)

### Candidates
- `GET /candidates` — List candidates for a job (ranked)
- `GET /candidates/{id}` — Full profile (scores, evidence, flags, evaluation)
- `POST /candidates/{id}/shortlist` — Shortlist (human only)
- `POST /candidates/{id}/decision` — Record final decision (human only)

### Approvals
- `GET /approvals` — Pending draft queue
- `POST /approvals/{id}/approve` — Approve draft (human)
- `POST /approvals/{id}/reject` — Reject draft (human)

### Other
- `GET /health` — Health check
- `GET /digest/today` — Daily summary
- `GET /audit` — Audit log (append-only)
- `GET /portal/{token}` — Candidate portal (public, token-protected)
- `POST /portal/{token}/video` — Submit interview response

## Data Model

### Tables

| Table | Purpose |
|-------|---------|
| `users` | Recruiters and admins |
| `jobs` | Job postings with rubrics |
| `candidates` | Candidate identity (name, email) |
| `applications` | Application + anonymized profile + CV path + status |
| `scores` | Scoring results (criteria, total, evidence) |
| `interview_questions` | Questions per job (can be tailored per application) |
| `video_submissions` | One-time token, transcript, used flag |
| `evaluations` | Interview evaluation (per-question scores, recommendation) |
| `drafts` | Pending emails (invite/reply/reminder/rejection) awaiting approval |
| `emails` | Incoming emails (category, urgency, flagged for human) |
| `audit_logs` | Append-only log (never updated or deleted) |

### Key Design Patterns

- **No raw passwords**: All stored as Argon2 hashes
- **JSON columns**: `rubric_json`, `anonymized_profile_json`, `criteria_json`, etc. for flexibility
- **Append-only audit**: No updates/deletes on `audit_logs`
- **Anonymized profile**: CV data with PII removed, stored per application
- **One-time portal tokens**: Hash stored only, never the token itself
- **Status enum**: Fixed valid transitions enforced in code

## LLM Integration

### Config

```env
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=...
LLM_MODEL=meta-llama/llama-2-7b-chat
LLM_FALLBACK_MODELS=gpt-4,gpt-3.5-turbo
LLM_TEMPERATURE=0
LLM_CACHE_ENABLED=true
LLM_MAX_ATTEMPTS=2
```

### Usage

```python
from app.llm import complete_json
from app.schemas import ScoringResult

result = complete_json(
    task="score",
    system="You are an expert recruiter...",
    user=f"Score this candidate:\n{anonymized_profile}",
    schema=ScoringResult,
    prompt_version="v1",
    db=session,
)
```

**Features:**
- **Caching**: `./backend/data/llm_cache/` (disk-based)
- **Validation**: Output validated against Pydantic schema; retry once on invalid JSON
- **Fallbacks**: Multiple models per API call (if supported)
- **Audit**: Each call logged to `audit_logs`
- **Graceful failure**: Raises clear error if `LLM_API_KEY` is empty

## Extension Guide

### Adding a New Capability

1. **Create a service** in `app/services/my_feature.py` with plain functions
2. **Create a Pydantic schema** in `app/schemas.py` for LLM output
3. **Create a prompt** in `backend/prompts/my_task.md` (versioned)
4. **Create a route** in `app/routes/my_feature.py`
5. **Register the route** in `app/main.py` (auto-imports all routes from `app/routes/`)
6. **Add tests** in `backend/tests/test_my_feature.py`
7. **Add frontend page** in `frontend/src/pages/MyFeature.jsx`

### HITL (Human-in-the-Loop) Rule

Any route that changes candidate status or sends an email MUST:
1. Go through `state_machine.transition()` (enforces valid state + HITL checks)
2. Create a `Draft` record in the approval queue (status = PENDING)
3. Wait for a human to approve (`POST /approvals/{id}/approve`)
4. Only then execute the actual action (send email, update status)

**Never permit AI to directly update status or send emails.** Always require human approval.

## Testing

```bash
# Install test dependencies (in requirements.txt)
pip install pytest httpx

# Run tests
pytest backend/tests/

# Specific test
pytest backend/tests/test_hitl.py -v

# The HITL test proves AI cannot enter human-only states
```

## Development Tips

### Frontend

- **Mock mode**: `docker-compose up` sets `VITE_USE_MOCK=false` by default
- **Test pages independently**: Visit http://localhost:5173 and check page
- **Mock data**: Edit `frontend/src/api/mock.js` to test UI logic
- **Tailwind live**: Changes to `.jsx` reload instantly via Vite

### Backend

- **API docs**: http://localhost:8000/docs (auto-generated Swagger UI)
- **Debug mode**: `APP_ENV=dev` logs SQL queries
- **Database**: `backend/data/hireguard.db` (SQLite file, delete to reset)
- **Audit log**: Query `audit_logs` to trace all actions

### Database Reset

```bash
rm backend/data/hireguard.db
python backend/scripts/seed.py
```

## Security Baseline

- **CSP headers**: Content-Security-Policy, X-Frame-Options, X-Content-Type-Options
- **CORS allowlist**: `CORS_ORIGINS` env var (defaults to localhost:5173)
- **Rate limiting**: `/auth/login` and `/portal/*` have stricter limits (via `slowapi`)
- **Password hashing**: Argon2 (not SHA256, not md5)
- **Session cookies**: HttpOnly + SameSite=Lax
- **ORM-only queries**: No raw SQL strings (SQLModel enforces parameterization)
- **Upload validation**: Stubs in `app/services/security_gate.py` (file type, hidden text)

## Deployment

### Backend

```bash
# Build
docker build -t hireguard-backend ./backend

# Run
docker run -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./data/hireguard.db \
  -e LLM_API_KEY=... \
  hireguard-backend
```

### Frontend

```bash
cd frontend
npm run build
# Upload `dist/` to Vercel, Netlify, or static host
```

### Database

SQLite file is portable. Back it up regularly if production data is stored.

## Troubleshooting

### Backend won't start
```bash
# Check port 8000 is free
# Check DATABASE_URL path is writable
# Check LLM_API_KEY if you want to test LLM endpoints
```

### Frontend can't connect to backend
```bash
# Check backend is running on port 8000
# Check VITE_USE_MOCK setting
# Check browser console for CORS errors
# Ensure CORS_ORIGINS in .env includes http://localhost:5173
```

### Database locked error
```bash
# SQLite can have concurrency issues
# Close all backend processes
# Delete .db file and re-seed
```

## Next Steps for Hackathon

- [ ] **Implement security gate**: File upload, hidden text detection, prompt injection
- [ ] **Implement parser**: Extract text/structure from PDF/DOCX
- [ ] **Implement scorer**: Call LLM to score criteria with evidence
- [ ] **Implement anonymizer**: Remove PII from parsed CV
- [ ] **Implement evaluator**: Call LLM to evaluate interview responses
- [ ] **Implement transcriber**: Convert audio/video to text (faster-whisper)
- [ ] **Implement mailer**: Send emails via SMTP
- [ ] **Implement inbox watcher**: Poll IMAP for new applications
- [ ] **Add session auth**: Actual session cookies (not just stub)
- [ ] **Add frontend auth guard**: Redirect to login if not authenticated

## License

MIT (for hackathon)
