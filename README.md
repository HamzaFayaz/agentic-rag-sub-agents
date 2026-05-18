# agentic-rag-sub-agents

Production-oriented RAG application with chat and document ingestion. **Module 1** (current): auth, threaded chat, Supabase-backed history, streaming Chat Completions, LangSmith tracing. No RAG yet.

## Prerequisites (you)

1. [Supabase](https://supabase.com) project with **Email** auth enabled
2. [OpenAI](https://platform.openai.com) API key (`gpt-4o-mini` recommended)
3. Optional: [LangSmith](https://smith.langchain.com) for tracing

## Quick start

### 1. Database migration

Run `supabase/migrations/001_threads_messages.sql` in the Supabase **SQL Editor**. Confirm `threads` and `messages` tables exist with RLS enabled.

### 2. Environment

```bash
cp .env.example backend/.env
cp .env.example frontend/.env
```

Fill in `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `OPENAI_API_KEY`, and matching `VITE_*` values.

### 3. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health check: `curl http://localhost:8000/health`

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — sign up, create a chat, send a message.

## Project layout

```
backend/app/          FastAPI (chat stream, JWT auth)
frontend/src/         React chat UI
supabase/migrations/  Postgres schema + RLS
.agent/plans/         Build plans
```

## RLS smoke test

1. Create User A and User B (separate sign-ups)
2. User A creates a thread and note its UUID
3. As User B, confirm the thread is not visible in the UI
4. Optional: `curl /api/chat/stream` with User B's JWT and User A's `thread_id` → expect **403**

## Docs

- `PRD.md` — full product scope
- `cursor.md` — agent conventions
- `PROGRESS.md` — module checklist
- `.agent/plans/1.app-shell.md` — Module 1 task cards
