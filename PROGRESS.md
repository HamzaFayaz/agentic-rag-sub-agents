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

## Modules 4 + 5 + 6 — Robust Retrieval Upgrade — **complete & validated** *(branch `module-4-5-6-retrieval`)*

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

### Module 4: Metadata Extraction — **complete & validated**

- [x] Migration `004_metadata.sql`: `documents.metadata` jsonb + doc_type index
- [x] Backend: `MetadataExtractor` + Pydantic schema; fail-open during ingest
- [x] Retrieval: apply metadata filters in search path *(deferred — optional v1)*
- [x] Frontend: doc_type / topics / summary on Documents list

### Module 5: Multi-Format Support — **complete & validated**

- [x] `parsing.py` — docling with pypdf/plain-text fallback
- [x] Structure-aware chunking with parent–child for long sections
- [x] Migration `005_chunk_structure.sql`
- [x] Upload accepts `.docx`, `.html`; MIME validation updated

### Module 6: Hybrid Search & Reranking — **complete & validated**

- [x] Migration `006_hybrid_search.sql` — `content_tsv`, `match_chunks_keyword` RPC
- [x] `HybridSearchService` — vector + keyword, RRF merge
- [x] `CohereReranker` — fail-open without key
- [x] Config: `COHERE_API_KEY`, `RERANK_*`, `HYBRID_CANDIDATE_K`

**Validation** *(plan 4.modules-4-5-6 — passed 2026-05-29, E2E on `module-4-5-6-retrieval`)*

- [x] Migrations `004`, `005`, `006` applied in Supabase SQL Editor
- [x] Upload `.txt` / `.md` / `.pdf` → `ready` with `metadata.parser` + `metadata.llm` (e.g. CV PDF)
- [x] Chat streams after ingest (`stream=True` fix); grounded answers with sources
- [x] Documents list loads with `metadata` column; upload path fixes (`maybe_single`, docling scalars)
- [x] Re-upload unchanged file → `unchanged` (Module 3 + M4 skip)
- [x] Hybrid pipeline wired: vector + FTS → RRF → Cohere rerank → parent context
- [x] LangSmith full RAG tracing spans (optional, when `LANGSMITH_TRACING=true`)

**Known limitation (not a blocker):** PDF/Word with headings in the **same font** may get **FIXED** chunking (regex needs `#` markdown lines). See local `Notes/chunking-strategies.md`.

### LangSmith full tracing

- [x] P0 — `tracing.py` helper + `LANGSMITH_LOG_CHUNK_TEXT`
- [x] P1 — `chat_turn` + `rag_retrieve`
- [x] P2 — `hybrid_rrf` + `cohere_rerank`
- [x] P3 — `build_rag_prompt`
- [x] P4 — `document_ingest` + `metadata_extract`
- [x] P5 — `embed_texts`
- [x] P6 — README, `.env.example`, PROGRESS
- Plan: [.agent/plans/5.langsmith-full-tracing.md](.agent/plans/5.langsmith-full-tracing.md)

---

## Module 7 — Multi-Tool Agent — **complete & validated** *(branch `module-7-multi-tool-agent`)*

Replace always-on RAG with an LLM tool-calling loop. Three tools:

| Tool | Use case |
|------|----------|
| `search_documents` | Document prose / content (hybrid RAG) |
| `query_database` | Counts, lists, filters on library metadata (safe SQL views) |
| `web_search` | Online / current / external info (Tavily, fail-open) |

**RAG vs SQL:** chunk `content` = RAG only. Row stats and `documents.metadata` labels = SQL on `v_user_document_stats`, `v_user_chunk_meta`, `v_user_chat_stats`.

### Checklist

- [x] P0 — Config flags, `.env.example`, tool contracts + SSE payloads
- [x] A — Safe views migration, SQL validator, TextToSqlService, executor
- [x] B — Tavily web search service + executor
- [x] C — RAG tool wrapper, ToolDispatcher
- [x] D — SSE `tool_start`/`tool_end`, attribution UI (SQL, web URLs, tool activity)
- [x] E — OpenAI tool-calling client, ChatService agent loop, chat route SSE
- [x] F — LangSmith tool spans, README / PROGRESS / release notes

**Validation** *(plan 6.module-7 — passed 2026-06-14; may re-run E2E later)*

- [x] Backend unit tests: 39/39 pytest (`sql_validator`, `text_to_sql`, `tool_dispatcher`, `web_search`, `openai_tools`, `tracing`)
- [x] Frontend: `tsc --noEmit` clean
- [x] Dev smoke: backend starts after `pip install -r requirements.txt` (Module 7 deps: `sqlparse`, `asyncpg`)
- [x] Documents page loads prior uploads when backend is running
- [x] `DATABASE_URL` wired for Text-to-SQL (direct Postgres connection)

**Re-test later** *(E2E — run when env or migrations change, or before GitHub release tag)*

- [ ] Doc content question → `search_documents` + source chips
- [ ] Library stats → `query_database` + SQL shown (`DATABASE_URL` + migration `007`)
- [ ] Web question → `web_search` + URL chips (`TAVILY_API_KEY`)
- [ ] SQL boundary: validator rejects `content` / `document_chunks` / `DELETE`
- [ ] RLS smoke test (User A / User B)

**Flow doc:** [Discussion/module-7-tool-routing-flow.md](Discussion/module-7-tool-routing-flow.md)

Plan: [.agent/plans/6.module-7-multi-tool-agent.md](.agent/plans/6.module-7-multi-tool-agent.md)

---

## Module 8 — Sub-Agents (Document Analyst) — **complete & validated** *(branch `module-8-sub-agents`)*

One new main-agent tool: `analyze_document`. The sub-agent has isolated context, token-aware single/multi pass routing, and returns a compact report to the main agent. No nested sub-agents; max 2 analyses per turn.

| Component | Role |
|-----------|------|
| `analyze_document` tool | Whole-doc summary, deep read, compare-by-filename |
| `DocumentAnalystService` | Single pass if doc fits budget; else map-reduce batches |
| Per-turn cap | `SUB_AGENT_MAX_PER_TURN=2` — block 3rd call in one message |
| RLS | Filename lookup scoped to current user's JWT |
| Parallel compare | Back-to-back `analyze_document` calls in one LLM step run concurrently |

### Checklist

- [x] P0 — Config flags, `.env.example`, `sub_agent_active()` helper
- [x] A — `total_token_count` migration, ingest write, repo chunk/filename helpers
- [x] B — `fits_budget`, `batch_chunks`, `DocumentAnalystService` (single + multi pass)
- [x] C — Tool contract, executor/dispatcher, chat loop + per-turn cap
- [x] D — `subagent_progress` SSE, frontend metadata + tool activity UI
- [x] E — LangSmith `document_analyze` spans, unit tests, README / PROGRESS / release notes
- [x] Ship polish — markdown chat UI, sub-agent step labels, parallel compare dispatch

**Validation** *(plan 7.module-8 — Track E + ship)*

- [x] Backend unit tests: `test_sub_agent.py`, updated `test_tool_dispatcher.py`
- [x] Budget routing: single vs multi pass; batch boundaries; pass cap
- [x] Per-turn cap logic; filename-not-found; RLS empty lookup
- [x] `analyze_document` gated when `SUB_AGENT_ENABLED=false`
- [x] Parallel grouping for consecutive `analyze_document` tool calls

**Re-test later** *(E2E — run when env or migrations change, or before GitHub release tag)*

- [ ] "Summarize my whole handbook" → 1 `analyze_document`, progress chip
- [ ] "Compare contract A vs contract B" → 2 analyses, synthesized answer
- [ ] Normal fact question → `search_documents` only
- [ ] 3rd analyze call in one turn → blocked by per-turn cap
- [ ] Unknown filename → helpful error listing available docs
- [ ] RLS smoke test (User A / User B)
- [ ] `SUB_AGENT_ENABLED=false` → tool omitted; chat still works

Plan: [.agent/plans/7.module-8-sub-agents.md](.agent/plans/7.module-8-sub-agents.md)

---

## Phase 9 — Optimization, Memory & Security — **not started**

**Next phase for this project.** Work begins with **optimization** (profile hot paths, reduce latency/token cost), then **memory** (token-budget history + rolling thread summaries), then **security** (rate limits, upload hardening, RLS/SQL audit, prompt-injection guardrails).

**Execution order:** Optimization → Memory + Security (parallel after optimization gate).

**Branch:** `phase-9-optimization-memory-security` (from `main`)

| Track | Focus |
|-------|--------|
| **O — Optimization** | Baseline benchmarks, embedding batching, ingest short-circuit, retrieval tuning, agent loop compaction, DB indexes |
| **M — Memory** | Thread summary schema, token-budget history window, rolling summary, UI indicator |
| **S — Security** | Rate limiting, upload validation, SQL/RLS tests, prompt-injection guardrails, security headers |

### Checklist

- [ ] P0 — Baseline benchmark script + Phase 9 config flags
- [ ] Track O — Optimization (complete before M/S)
- [ ] Track M — Memory
- [ ] Track S — Security
- [ ] Track E — Integration tests, docs, v6 release notes

Plan: [.agent/plans/8.optimization-memory-security.md](.agent/plans/8.optimization-memory-security.md)
