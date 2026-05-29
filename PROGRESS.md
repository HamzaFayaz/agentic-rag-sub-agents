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

### Module 3: Record Manager — **complete & validated**

- [x] Migration `003_record_manager.sql`: `content_hash`, unique `(user_id, filename)`
- [x] Backend: SHA-256 hashing, filename lookup, skip unchanged / update in place
- [x] API: `ingest_action` + `content_hash` on upload response
- [x] Frontend: upload outcome messages; `useDocuments` handles `unchanged`

**Validation** *(plan P5-T1 — passed 2026-05-29)*

- [x] Upload `samples/rag-test-document.txt` → `ingest_action: created`, status `ready`
- [x] Re-upload same file → `unchanged`, no duplicate row
- [x] Edit one line, re-upload same name → `updated`, same `id`
- [x] Chat still retrieves chunks for that filename
- [x] User B: same bytes, different user → independent row (RLS)

---

## Current focus: Modules 4 + 5 + 6 (single delivery)

**Approach:** Build Modules 4, 5, and 6 together as one robust retrieval upgrade — not three separate releases. Shared ingest/retrieve path: better parsing → document metadata → hybrid search + reranking → same small-context chat flow (never pass full docs to the LLM).

| Module | Role in combined build |
|--------|-------------------------|
| **4 — Metadata extraction** | LLM structured metadata at ingest; filter/narrow retrieval by document fields |
| **5 — Multi-format support** | Docling (or equivalent) for PDF/DOCX/HTML/Markdown; cleaner text → better chunks |
| **6 — Hybrid search & reranking** | Keyword + vector (RRF), then rerank top candidates before prompt injection |

**Target pipeline**

```text
Upload → parse (M5) → metadata extract (M4) → chunk → embed
Chat   → optional metadata filters (M4) → hybrid retrieve (M6) → rerank (M6) → top-K → LLM
```

### Module 4: Metadata Extraction — **in progress** *(with M5 + M6)*

- [ ] Migration: `documents.metadata` (jsonb) + indexes as needed for filters
- [ ] Backend: Pydantic schema + LLM extraction during ingest (skip on `unchanged`)
- [ ] Retrieval: apply metadata filters in `match`/search path
- [ ] Frontend: show document metadata on Documents list/detail (optional filters later)

### Module 5: Multi-Format Support — **in progress** *(with M4 + M6)*

- [ ] Replace/extend parsing with docling for PDF, DOCX, HTML, Markdown
- [ ] Upload API accepts new types; size/MIME validation updated
- [ ] Cascade delete unchanged (document, chunks, storage)
- [ ] `.env.example` / README updated for new formats and dependencies

### Module 6: Hybrid Search & Reranking — **in progress** *(with M4 + M5)*

- [ ] Supabase: full-text / keyword search on `document_chunks` (or parallel RPC)
- [ ] Backend: hybrid retrieval (vector + keyword, RRF merge)
- [ ] Backend: reranker step (wider candidate pool → top-N for prompt)
- [ ] Config: env vars for hybrid weights, rerank model, candidate counts
- [ ] Validation: exact-term queries + paraphrase queries beat vector-only baseline

**Combined validation (E2E)**

- [ ] Upload mixed formats (txt, md, pdf, docx) → `ready` with metadata populated
- [ ] Chat: paraphrased question retrieves correct passage (vector + rerank)
- [ ] Chat: exact token (SKU, section cite, name) retrieves correct passage (hybrid)
- [ ] Metadata filter narrows to correct document when library has similar topics
- [ ] Re-upload unchanged file skips re-extract and re-embed (Module 3 + M4)
