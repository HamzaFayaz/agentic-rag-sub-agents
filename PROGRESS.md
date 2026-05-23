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

### Module 2: BYO Retrieval + RAG
