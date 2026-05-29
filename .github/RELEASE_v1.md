## Module 1: App Shell + Observability

Complete application shell with:

- React + Vite + Tailwind frontend
- Python + FastAPI backend
- Supabase Auth (email/password sign-up and login)
- Chat UI with thread management
- Streaming chat via Chat Completions API and SSE
- Message history persistence in Supabase Postgres
- Row-Level Security on all tables
- LangSmith tracing on chat requests
- `.env.example` with required configuration keys documented

## Module 2: BYO Retrieval + RAG

Retrieval-augmented chat with:

- Supabase pgvector: `documents`, `document_chunks`, storage RLS, `match_document_chunks` RPC, message `metadata`, Realtime on `documents`
- Private `documents` storage bucket (dashboard setup)
- Backend ingestion: upload → chunk → embed → index; documents API; RAG chat with SSE `sources`
- Frontend Documents page (upload, list, status, realtime, delete) and chat source citations
- `.env.example` and README updated for Module 2 setup and usage
