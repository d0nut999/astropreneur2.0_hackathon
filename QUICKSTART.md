# HR Buddy Quickstart (10 minutes)

## 1. Start Services (1 minute)

```bash
cp backend/.env.example backend/.env
docker-compose up
```

Wait for output:
```
hireguard_frontend | VITE v5.0.0 ready in XXX ms
hireguard_backend | Uvicorn running on http://0.0.0.0:8000
```

## 2. Seed Database (1 minute)

In a new terminal:

```bash
python backend/scripts/seed.py
```

Output:
```
✅ Database seeded successfully!

Credentials:
Admin:    admin@fictional-company.test / admin123
Recruiter: recruiter@fictional-company.test / recruiter123
```

## 3. Open the App (30 seconds)

- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **Mailpit Inbox**: http://localhost:8025

## 4. Test It (2 minutes)

1. Go to http://localhost:5173
2. Login with `recruiter@fictional-company.test` / `recruiter123`
3. You'll see:
   - Dashboard with metrics
   - Jobs list (1 demo job)
   - Approvals queue (1 pending draft)
   - Audit log

## 5. Test Mock Mode (Optional)

To test frontend without backend running:

```bash
# In docker-compose.yml, change frontend env:
VITE_USE_MOCK=true
```

Then restart frontend. All pages work with mock data.

## Key Concepts

### State Machine (HITL)

Candidates move through states: `RECEIVED → SCREENED → SCORED → SHORTLISTED* → INVITED* → VIDEO_SUBMITTED → EVALUATED → DECIDED*`

`*` = Human must click to advance. AI cannot force these.

### Approval Queue

Email drafts wait in `/approvals` until a human clicks Approve. Only then is the email sent.

### Audit Log

Every action (`/audit`) is append-only. No edits or deletes. Full traceability.

## What's Ready to Build

| Component | Status | Next Step |
|-----------|--------|-----------|
| Project structure | ✅ Done | Start coding features |
| Database models | ✅ Done | Add fields if needed |
| State machine | ✅ Done, tested | Enforce in business logic |
| API stubs | ✅ Mock data | Replace with real logic |
| Frontend pages | ✅ Placeholders | Add forms, real data binding |
| LLM wrapper | ✅ Stub | Integrate real LLM calls |
| Security baseline | ✅ Headers + rate limit | Add auth guard, upload checks |

## Your Team's Next Tasks

### Task 1: CV Upload & Security Check
- `POST /candidates/{id}/upload_cv`
- Call `app.services.security_gate.check_upload(path)`
- Store flags, set status to SCREENED or QUARANTINED

### Task 2: CV Parsing & Anonymization
- `POST /candidates/{id}/parse_cv`
- Call `app.services.parser.parse_cv(path)` → `app.services.anonymizer.anonymize_profile(parsed)`
- Store `anonymized_profile_json`

### Task 3: Scoring
- `POST /candidates/{id}/score`
- Call `app.services.scorer.score_candidate(...)`
- Create Score record, set status to SCORED

### Task 4: Interview Questions & Transcription
- `GET /jobs/{id}/questions` — Return interview questions
- `POST /portal/{token}/video` — Accept video upload
- Call `app.services.transcriber.transcribe_video(path)`
- Store transcript

### Task 5: Evaluation
- `POST /candidates/{id}/evaluate`
- Call `app.services.evaluator.evaluate_interview(...)`
- Create Evaluation record, set status to EVALUATED

### Task 6: Frontend Forms
- Add CV upload form to candidate detail page
- Add approve/reject buttons in approval queue
- Add video player + question form to portal

## Debugging

### Backend logs
```bash
docker logs -f hireguard_backend
```

### Frontend logs
```bash
docker logs -f hireguard_frontend
```

### Database
```bash
sqlite3 backend/data/hireguard.db ".tables"
```

### API test
```bash
curl http://localhost:8000/docs
```

## Tips

- **Mock data**: See `frontend/src/api/mock.js` — easy to add more responses
- **LLM not set**: Leave `LLM_API_KEY` empty; routes that need it will fail gracefully
- **State transitions**: Use `state_machine.transition()` to enforce HITL rules
- **Never hardcode PII**: All test data is fictional
- **Audit everything**: Call `audit.log_audit()` after any state/data change

## Good luck! 🚀

Questions? Check README.md or API docs at http://localhost:8000/docs
