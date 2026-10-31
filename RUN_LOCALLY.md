# Run HireGuard on your laptop (Windows, no Docker needed)

You need: **Python 3.11+** and **Node.js 18+**.

## 1. Backend (terminal 1)

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Open `backend/.env` and paste your free Groq key (https://console.groq.com → API Keys):

```
LLM_API_KEY=gsk_...
```

Then:

```bash
python scripts/seed.py
python -m uvicorn app.main:app --reload --port 8000
```

Leave this terminal open. API docs: http://localhost:8000/docs

> Mac/Linux: use `source venv/bin/activate` and `cp .env.example .env`.

## 2. Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 → **Today** → **Load demo emails**.

## 3. Optional: emails arriving "live" (Mailpit)

Mailpit is a fake mail server with a web inbox. Needs Docker Desktop:

```bash
docker run -d -p 8025:8025 -p 1025:1025 axllent/mailpit
cd backend
python scripts/send_demo_emails.py 01 07 12
```

Then in HireGuard → **Inbox** → **Sync inbox**. Approved replies also appear at http://localhost:8025.

## Without an API key?

Everything still works: HireGuard falls back to offline rules (marked "offline rules" in the Inbox).
With a Groq key, summaries and meeting detection are smarter.

## After pulling new code

If the database structure changed, delete the old database and seed again:

```bash
cd backend
del data\hireguard.db
python scripts/seed.py
```

## Tests

```bash
cd backend
python -m pytest -q
```
