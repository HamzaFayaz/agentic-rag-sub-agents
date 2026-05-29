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

## Modules 4 + 5 + 6 — Robust Retrieval Upgrade — **implemented** *(branch `module-4-5-6-retrieval`)*

**Approach:** Single delivery — docling parsing → document metadata → hybrid search + reranking → same small-context chat flow.

| Module | Role |
|--------|------|
| **4 — Metadata extraction** | One `gpt-4o-mini` structured call per new/changed doc → `metadata.llm`; fail-open |
| **5 — Multi-format + chunking** | Docling parse; rule router (FIXED / SECTION / parent–child); `.txt`, `.md`, `.pdf`, `.docx`, `.html` |
| **6 — Hybrid + rerank** | Vector + FTS → RRF → Cohere rerank → parent context expansion |

**Pipeline**

```text
Upload → parse (M5) → metadata.parser → chunk → metadata.llm (M4) → embed children → ready
Chat   → hybrid (M6) → rerank (M6) → parent context → top-K → LLM
```

### Module 4: Metadata Extraction — **complete**

- [x] Migration `004_metadata.sql`: `documents.metadata` jsonb + doc_type index
- [x] Backend: `MetadataExtractor` + Pydantic schema; fail-open during ingest
- [ ] Retrieval: apply metadata filters in search path *(deferred — optional v1)*
- [x] Frontend: doc_type / topics / summary on Documents list

### Module 5: Multi-Format Support — **complete**

- [x] `parsing.py` — docling with pypdf/plain-text fallback
- [x] Structure-aware chunking with parent–child for long sections
- [x] Migration `005_chunk_structure.sql`
- [x] Upload accepts `.docx`, `.html`; MIME validation updated

### Module 6: Hybrid Search & Reranking — **complete**

- [x] Migration `006_hybrid_search.sql` — `content_tsv`, `match_chunks_keyword` RPC
- [x] `HybridSearchService` — vector + keyword, RRF merge
- [x] `CohereReranker` — fail-open without key
- [x] Config: `COHERE_API_KEY`, `RERANK_*`, `HYBRID_CANDIDATE_K`

**Combined validation (E2E)** — *apply migrations 004–006 in Supabase, then run:*

- [ ] Upload mixed formats (txt, md, pdf, docx) → `ready` with `metadata.parser` + `metadata.llm`
- [ ] Chat: paraphrased question retrieves correct passage (vector + rerank)
- [ ] Chat: exact token retrieves correct passage (hybrid keyword leg)
- [ ] Parent–child doc: answer uses expanded section context
- [ ] Re-upload unchanged file skips re-extract and re-embed (Module 3 + M4)
- [ ] Rerank fail-open: works with `RERANK_ENABLED=false` or missing `COHERE_API_KEY`

### LangSmith full tracing

- [x] P0 — `tracing.py` helper + `LANGSMITH_LOG_CHUNK_TEXT`
- [x] P1 — `chat_turn` + `rag_retrieve`
- [x] P2 — `hybrid_rrf` + `cohere_rerank`
- [x] P3 — `build_rag_prompt`
- [x] P4 — `document_ingest` + `metadata_extract`
- [x] P5 — `embed_texts`
- [x] P6 — README, `.env.example`, PROGRESS
- Plan: [.agent/plans/5.langsmith-full-tracing.md](.agent/plans/5.langsmith-full-tracing.md)
