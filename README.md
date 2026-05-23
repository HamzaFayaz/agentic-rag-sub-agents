# agentic-rag-sub-agents

Production-oriented RAG application with chat and document ingestion. **Module 1**: auth, threaded chat, Supabase-backed history, streaming Chat Completions, LangSmith tracing. **Module 2**: document upload, chunking, embeddings (pgvector), retrieval-augmented chat with source citations.

## Prerequisites (you)

1. [Supabase](https://supabase.com) project with **Email** auth enabled
2. [OpenAI](https://platform.openai.com) API key (`gpt-4o-mini` + `text-embedding-3-small`)
3. Optional: [LangSmith](https://smith.langchain.com) for tracing

## Quick start

### 1. Database migrations

Run in the Supabase **SQL Editor**, in order:

1. `supabase/migrations/001_threads_messages.sql`
2. `supabase/migrations/002_documents_rag.sql`

Confirm `threads`, `messages`, `documents`, and `document_chunks` exist with RLS enabled.

### 2. Storage bucket

Dashboard → **Storage** → create a **private** bucket named `documents`.

### 3. Environment

```bash
cp .env.example backend/.env
cp .env.example frontend/.env
```

Fill in `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `OPENAI_API_KEY`, and matching `VITE_*` values.

Module 2 backend vars (defaults in `.env.example`):

- `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`
- `RAG_TOP_K`, `RAG_MATCH_THRESHOLD`, `MAX_UPLOAD_BYTES`, `CHUNK_SIZE`, `CHUNK_OVERLAP`

### 4. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health check: `curl http://localhost:8000/health`

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — sign up, upload documents on **Documents**, then chat with RAG on **Chat**.

## API (Module 2)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/documents` | List current user's documents |
| `POST` | `/api/documents/upload` | Multipart file upload (`.txt`, `.md`, `.pdf`) |
| `DELETE` | `/api/documents/{id}` | Delete document, chunks, and storage object |
| `POST` | `/api/chat/stream` | SSE chat; emits `sources` then `token` events |

## Project layout

```
backend/app/          FastAPI (chat stream, documents, RAG)
frontend/src/         React chat + documents UI
supabase/migrations/  Postgres schema + RLS + pgvector RPC
.agent/plans/         Build plans
```

## RLS smoke test

1. Create User A and User B (separate sign-ups)
2. User A uploads a document and asks a question grounded in it
3. As User B, confirm the document is not visible and chat does not retrieve User A's chunks
4. Optional: `curl /api/chat/stream` with User B's JWT and User A's `thread_id` → expect **403**

## Docs

- `PRD.md` — full product scope
- `cursor.md` — agent conventions
- `PROGRESS.md` — module checklist
- `.agent/plans/2.byo-retrieval-rag.md` — Module 2 task cards
