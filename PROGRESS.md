# Progress

Track your progress through the masterclass. Update this file as you complete modules - Claude Code reads this to understand where you are in the project.

## Convention
- `[ ]` = Not started
- `[-]` = In progress
- `[x]` = Completed

## Modules

### Module 1: App Shell + Observability (LLM chat only — no RAG) — **complete**

- [x] Supabase project: Auth + `threads` / `messages` tables with RLS *(migration applied in dashboard — `supabase/migrations/`)*
- [x] FastAPI backend: load history → Chat Completions → stream reply → save messages
- [x] React chat UI: thread list, message view, SSE streaming
- [x] LangSmith tracing on chat requests *(tracing enabled and verified)*
- [x] `.env.example` with required keys documented

**Not in Module 1:** ingestion UI, embeddings, pgvector, retrieval tools, OpenAI Responses API / `file_search`

### Module 2: BYO Retrieval + RAG — **complete & validated**

- [x] Supabase: pgvector, `documents` / `document_chunks`, storage RLS, `match_document_chunks` RPC, message `metadata`, Realtime on `documents`
- [x] Private `documents` storage bucket (manual dashboard step)
- [x] Backend: upload → chunk → embed → index; documents API; RAG in chat with SSE `sources`
- [x] Frontend: Documents page (upload, list, status, realtime, delete); chat source citations
- [x] `.env.example` and README updated for Module 2

**Validation** *(plan P5-T5 — passed 2026-05-29)*

- [x] E2E: upload document → status reaches `ready` (Realtime) → chat answer grounded in content with source citations
- [x] SSE: `sources` event before `token` stream; citations persist after page refresh
- [x] RLS: second user cannot list, retrieve, or chat over another user's documents/chunks
- [x] Delete: document row, chunks, and storage object removed together

### Module 3: Record Manager — **in progress**

- [x] Migration `003_record_manager.sql`: `content_hash`, unique `(user_id, filename)`
- [x] Backend: SHA-256 hashing, filename lookup, skip unchanged / update in place
- [x] API: `ingest_action` + `content_hash` on upload response
- [x] Frontend: upload outcome messages; `useDocuments` handles `unchanged`
- [ ] E2E validation (re-upload skip, edit re-upload, RLS)
