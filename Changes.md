# TASK: Turn the existing frontend/backend skeleton into the base foundation for "HR Buddy"

## 0. Context

We are a team of 4 (mixed experience, some beginners) in a 16-hour hackathon ("Secure AI HR System"). HR Buddy is an AI recruiting assistant that:
- reads an HR inbox (application emails + CV attachments),
- screens CVs through a security gate (file checks, hidden-text and prompt-injection detection),
- anonymizes and scores candidates against an HR-approved job rubric, with quoted evidence,
- drafts invite/reply/reminder emails,
- runs an async video interview (the transcript is evaluated, never face/voice/emotion),
- recommends Advance / Hold / Not recommended.

Golden rule: **the agent executes, the human decides about people.** Nothing is sent and no candidate state changes without an HR click.

Core design principle: **"the reader can't act, the actor can't read."** The LLM reads untrusted content (CVs, emails, transcripts) and may ONLY return JSON. It has no tools. Sending email, changing status and writing records are done by normal code behind human-approved endpoints.

THIS TASK = FOUNDATION ONLY. Build the structure, config, data layer, stubs and mock endpoints so the team can work in parallel. Do NOT implement real AI logic, parsing, scoring or transcription yet.

## 1. Working rules (important)

1. **First inspect** the current repo (folders, dependencies, docker files, env files, README). Then post a short plan listing which existing files you will change, which you will create, and which you will delete. Wait for confirmation only if something conflicts with this spec; otherwise proceed.
2. **Make targeted edits to existing files. Do NOT regenerate or overwrite whole files** unless the file is empty or must be removed entirely. Preserve anything already working.
3. If the existing frontend is not React + Vite, stop and tell me before changing frameworks.
4. Keep everything runnable at every step. After each numbered section below, the project should still start.
5. Prefer simple, readable code over clever abstractions. Add short comments only where the intent is not obvious.
6. All data is FICTIONAL. Never add real personal data. Never commit secrets.
7. Everything must be easy to extend: follow the "Extension rules" in section 12.

## 2. Final tech stack

**Backend (Python 3.11+)**
- FastAPI + Uvicorn
- SQLModel on **SQLite** (single file, no Postgres)
- pydantic-settings for config from `.env`
- argon2-cffi for password hashing; session cookie auth (HttpOnly, SameSite=Lax); 2 roles: `recruiter`, `admin`
- slowapi for rate limiting; security-headers middleware; CORS allow-list
- OpenAI-compatible client (`openai` package) for the LLM, so we can switch between OpenRouter, Gemini's OpenAI-compatible endpoint, Groq or Ollama by changing env vars only
- PyMuPDF, python-magic, python-docx, pdfplumber (security gate and parsing, later)
- rapidfuzz (evidence quote verification, later)
- faster-whisper + ffmpeg (transcription, later; import lazily so the app starts without model downloads)
- stdlib imaplib/smtplib for email (Mailpit in dev)
- pytest + httpx for tests; ruff for lint

**Frontend**
- React + Vite + TypeScript (use JS if the existing project is JS; do not convert)
- Tailwind CSS
- react-router-dom
- A small `api` client with a **mock mode** (see section 9)
- Do NOT use dangerouslySetInnerHTML anywhere for CV/LLM/email text

**Infra**
- docker-compose with 3 services: `backend`, `frontend`, `mailpit`
- Mailpit = fake SMTP server + inbox web UI + API (no Gmail OAuth)

## 3. Remove Postgres

- Remove the Postgres service, volumes and `depends_on` from docker-compose.
- Remove Postgres drivers (psycopg2, asyncpg, etc.) and any DATABASE_URL pointing to Postgres.
- Replace with `DATABASE_URL=sqlite:///./data/hireguard.db`. Mount `./backend/data` as a volume so the DB survives restarts.
- Search the whole repo for leftover "postgres", "psycopg", "asyncpg", "5432" references and clean them.

## 4. Backend structure

Adapt the existing folders to this layout (create only what is missing):

```
backend/
  app/
    main.py            # app factory, middleware, router registration
    config.py          # Settings (pydantic-settings)
    db.py              # engine, session dependency, init_db()
    models.py          # SQLModel tables + enums
    schemas.py         # Pydantic request/response + LLM JSON schemas
    auth.py            # hashing, session handling, require_role()
    audit.py           # append-only audit helper
    llm.py             # provider wrapper (section 6)
    state_machine.py   # candidate states + transition rules (section 7)
    security_headers.py
    routes/            # one file per area, auto-registered
      health.py auth.py jobs.py candidates.py approvals.py
      portal.py digest.py audit.py
    services/          # business logic, one file per capability (stubs now)
      inbox.py security_gate.py parser.py anonymizer.py scorer.py
      questions.py transcriber.py evaluator.py drafter.py mailer.py digest.py
    prompts/           # versioned prompt files (.md), one per LLM task
      extract.md score.md questions.md evaluate.md digest.md injection_check.md
  tests/
    test_health.py test_hitl.py test_injection.py test_upload.py
  data/                # sqlite file, uploads, llm cache (gitignored)
  requirements.txt
  Dockerfile
```

Dockerfile must install system packages `libmagic1` and `ffmpeg`.
Uploaded files must be stored outside any static/web root, under `backend/data/uploads/`, with random filenames.

## 5. Config and environment

Create `.env.example` (and make sure `.env` is gitignored) with:

```
APP_ENV=dev
SECRET_KEY=change-me
DATABASE_URL=sqlite:///./data/hireguard.db
CORS_ORIGINS=http://localhost:5173

# LLM (OpenAI-compatible)
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=
LLM_MODEL=
LLM_FALLBACK_MODELS=
LLM_TEMPERATURE=0
LLM_CACHE_ENABLED=true
LLM_MAX_ATTEMPTS=2

# Email (Mailpit in dev)
SMTP_HOST=mailpit
SMTP_PORT=1025
IMAP_HOST=
IMAP_PORT=
IMAP_USER=
IMAP_PASSWORD=
HR_MAILBOX=hr@fictional-company.test

# Limits
MAX_UPLOAD_MB=5
MAX_VIDEO_MB=100
PORTAL_TOKEN_TTL_HOURS=72
```

`config.py` exposes a typed `Settings` object. No hardcoded values elsewhere.

## 6. LLM wrapper (`llm.py`)

One function is the only way any code talks to an LLM:

```python
def complete_json(task: str, system: str, user: str, schema: type[BaseModel],
                  prompt_version: str = "v1") -> BaseModel
```

Requirements:
- Uses the OpenAI-compatible client with `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`.
- temperature = 0.
- If `LLM_FALLBACK_MODELS` is set, pass them as fallbacks (for OpenRouter via `extra_body={"models": [...]}`).
- Validates the output with the given Pydantic schema; on invalid JSON retry ONCE, then raise a clear error. Cap total attempts (`LLM_MAX_ATTEMPTS`) so retries cannot burn the free daily quota.
- **Disk cache**: key = hash(model + prompt_version + system + user), stored as JSON under `data/llm_cache/`. If cached, return it without calling the API. Controlled by `LLM_CACHE_ENABLED`.
- Writes an audit entry (actor=`ai`, action=task, payload hash, model, prompt_version).
- The wrapper exposes NO tool-calling or function-calling. Output is JSON only.
- If `LLM_API_KEY` is empty, raise a clear "LLM not configured" error (do not crash the app at startup).

## 7. Database models and state machine

Create SQLModel tables (SQLite). Keep fields minimal; JSON columns for flexible content:

- `User` (id, email, password_hash, role)
- `Job` (id, title, description, rubric_json, rubric_approved_by, created_at)
- `Candidate` (id, name, email) , identity stored separately from the anonymized profile
- `Application` (id, job_id, candidate_id, cv_path, status, security_flags_json, anonymized_profile_json, created_at)
- `Score` (id, application_id, criteria_json, total, model, prompt_version, created_at)
- `InterviewQuestion` (id, job_id, application_id nullable, text, rubric, is_tailored)
- `VideoSubmission` (id, application_id, path, token_hash, expires_at, used, transcript_json)
- `Evaluation` (id, application_id, per_question_json, recommendation, confidence, summary_json)
- `Draft` (id, application_id nullable, type, subject, body, status, approved_by, created_at) with type in `invite|reply|reminder|rejection` and status in `pending|approved|rejected|sent`
- `Email` (id, from_addr, subject, body, category, urgency, needs_human, injection_suspected, received_at)
- `AuditLog` (id, actor, action, entity, entity_id, payload_hash, timestamp), append-only: no update/delete helpers anywhere

Use enums for statuses. Add `init_db()` that creates tables on startup.

**`state_machine.py`:**

```
RECEIVED -> SCREENED | QUARANTINED
SCREENED -> SCORED
SCORED -> SHORTLISTED*
SHORTLISTED* -> INVITED*
INVITED* -> VIDEO_SUBMITTED
VIDEO_SUBMITTED -> EVALUATED
EVALUATED -> DECIDED*
```
`*` = only a human actor may enter this state. Implement `transition(application, to_state, actor)` where actor is `ai` | `system` | `user:<id>`. It must raise an error for invalid transitions and for any non-human actor entering a `*` state, and it must write an audit entry. All status changes in the codebase go through this function. Add a unit test in `tests/test_hitl.py` proving an `ai` actor cannot reach SHORTLISTED/INVITED/DECIDED.

## 8. API: stub endpoints with mock data

Implement these routes now, returning realistic MOCK JSON (hardcoded or from a `mock_data.py`), with the final response shapes defined in `schemas.py`, so frontend and backend can work in parallel:

```
GET  /health
POST /auth/login          POST /auth/logout        GET /auth/me
GET  /jobs                POST /jobs               POST /jobs/{id}/rubric/approve
GET  /jobs/{id}/candidates         (ranked list)
GET  /candidates/{id}              (profile, scores, evidence, flags, evaluation)
POST /candidates/{id}/shortlist    (human only)
POST /candidates/{id}/decision     (human only)
GET  /approvals           POST /approvals/{id}/approve    POST /approvals/{id}/reject
GET  /digest/today
GET  /audit
GET  /portal/{token}      POST /portal/{token}/video      (public, token-protected)
```

Rules:
- All routes except `/health`, `/auth/login` and `/portal/*` require a logged-in user via `require_role(...)`.
- Human-only endpoints (shortlist, decision, approve) must take the actor from the session, never from the request body.
- Add a `seed` script (`scripts/seed.py`) that creates one admin and one recruiter user with demo passwords read from env or printed once, plus a couple of mock jobs.

## 9. Frontend structure

```
frontend/src/
  api/
    client.ts          # fetch wrapper (credentials: "include"), base URL from env
    mock.ts            # mock responses matching schemas
    index.ts           # exports functions; uses mock when VITE_USE_MOCK=true
  components/          # shared UI (Layout, StatusBadge, EvidenceQuote, FlagBanner)
  pages/
    Login.tsx Dashboard.tsx Job.tsx Candidate.tsx
    Approvals.tsx Digest.tsx Audit.tsx Portal.tsx
  App.tsx              # routes + protected route wrapper
  main.tsx
```

- `VITE_USE_MOCK=true` makes every page work with mock data and no backend. `false` hits the real API.
- Pages can be simple placeholders showing a title and the mock data in a basic table or card list. No design polish yet.
- Render all CV/LLM/email text as plain text.
- `Portal.tsx` is public (token in the URL), with a file input for video/audio upload and a text-answer fallback. No MediaRecorder yet.
- Tailwind configured and working.

## 10. docker-compose and dev experience

- Services: `backend` (port 8000), `frontend` (port 5173), `mailpit` (SMTP 1025, web UI 8025).
- Backend and frontend mount source folders for hot reload.
- `docker-compose up` must start everything with no extra manual steps except copying `.env.example` to `.env`.
- Add a `Makefile` or `scripts/` with: `seed`, `reset_demo` (stub: clears DB and uploads), `test`.
- Create the `data/` folders (`jobs`, `cvs`, `cvs_malicious`, `emails`, `videos`) with a README line "FICTIONAL, generated for hackathon". Do not generate content yet.

## 11. Security baseline to wire now (thin, not complete)

- Security headers middleware (CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy).
- CORS allow-list from `CORS_ORIGINS`, credentials enabled only for those origins.
- slowapi limiter registered; stricter limit on `/auth/login` and `/portal/*`.
- Passwords hashed with argon2. Session cookie HttpOnly + SameSite=Lax.
- ORM-only queries (no raw SQL strings).
- `security_gate.py` and `parser.py` exist as stubs with the intended function signatures, e.g. `check_upload(path) -> GateResult`, `find_hidden_text(path) -> list[str]`. Do not implement logic yet.
- `tests/test_injection.py` and `tests/test_upload.py` exist with a single skipped placeholder test each.

## 12. Extension rules (keep it open)

Design so a new capability is added by creating files, not by editing core code:
1. **Routes auto-register**: `main.py` should include every router found in `routes/` (or a simple list in one place). Adding a feature = new file in `routes/`.
2. **Service per capability** in `services/`, with plain functions and typed inputs/outputs.
3. **Prompt per LLM task** in `prompts/` as `.md`, with a version string; `llm.py` takes task name + version.
4. **Schema per LLM task** in `schemas.py` (Pydantic), used for validation.
5. **Feature flags** in `config.py` (e.g. `FEATURE_DIGEST`, `FEATURE_SCHEDULING`, `FEATURE_FAQ`, `FEATURE_BIAS_TEST`), default on for MUST/SHOULD features and off for COULD ones. Routes for disabled features return 404.
6. **Frontend**: a new page = new file in `pages/` plus one route line plus one nav entry.
7. Any new outgoing email or status change MUST go through the approval queue (Draft table) and `state_machine.transition()`. Document this in the README as a contributor rule.

## 13. Current step process (pipeline) to keep in mind while structuring

1. Inbox watcher saves email + attachments, creates Application (RECEIVED).
2. Security gate checks the files; suspicious ones go to QUARANTINED, others SCREENED.
3. Parser creates structured JSON, anonymizer strips identity, stored in `anonymized_profile_json`.
4. Scorer returns per-criterion scores with evidence quotes (verified in code); total computed in Python; state SCORED.
5. HR approves the shortlist (human), then an invite Draft appears in the approval queue.
6. HR approves the draft, mailer sends it via SMTP, state INVITED.
7. Candidate uses a signed one-time link (token stored as hash only) to submit answers; state VIDEO_SUBMITTED.
8. Transcriber then evaluator produce the recommendation; state EVALUATED.
9. HR records the final decision (human); state DECIDED; everything is audit-logged.
Side flow: every incoming email gets classified (category, urgency, needs_human) for the daily digest.

Only the structure for steps 1-9 is needed now. Each step is a stub that other teammates will fill in.

## 14. Definition of done

- `cp .env.example .env && docker-compose up` starts backend, frontend and mailpit with no errors; no Postgres anywhere.
- `GET /health` returns OK; Mailpit UI opens on port 8025.
- `python scripts/seed.py` creates users; login works and `/auth/me` returns the user.
- Each stub route returns mock JSON; frontend with `VITE_USE_MOCK=true` shows all pages with data.
- `pytest` passes, including the state machine test that an `ai` actor cannot enter human-only states.
- `llm.complete_json` exists with caching, fallbacks and validation; it fails gracefully when no API key is set.
- README updated with: stack, how to run, folder map, state machine, and the extension rules.
- Final message: list of files changed/created/deleted and anything you were unsure about.

## 15. Do NOT do now

- No real CV parsing, scoring, transcription, email polling or evaluator logic.
- No Postgres, Redis, Celery, LangChain or any agent framework.
- No UI polish or component library installs beyond Tailwind.
- No full-file rewrites of existing files that already work.