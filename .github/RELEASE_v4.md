# Release v4 — Module 7: Multi-Tool Agent

**Status:** Complete & validated (2026-06-14). Tagged as **v4** on branch `module-7-multi-tool-agent`.

## Summary

Module 7 replaces always-on RAG with an **LLM tool-calling loop**. The model chooses among three tools per question, up to 3 iterations, then streams the final answer.

## Tools

| Tool | Purpose |
|------|---------|
| `search_documents` | Hybrid RAG over uploaded files (Modules 2–6) |
| `query_database` | Read-only SQL on safe metadata views |
| `web_search` | Tavily fallback for online/current questions |

## Text-to-SQL scope

- **IN:** counts, lists, filters, aggregates on `v_user_document_stats`, `v_user_chunk_meta`, `v_user_chat_stats`
- **OUT:** chunk text, embeddings, raw tables, writes/DDL
- **Enforcement:** safe views (Layer 1) + `sqlparse` validator (Layer 2) + RLS via user JWT

## UI

- SSE `tool_start` / `tool_end` during streaming
- SQL attribution (generated query shown)
- Web URL chips and doc source citations
- Tool activity status chips

## Configuration

See `.env.example` — `TEXT_TO_SQL_ENABLED`, `DATABASE_URL`, `TAVILY_API_KEY`, `AGENT_MAX_TOOL_ITERATIONS` (default 3).

## Migration

Apply `supabase/migrations/007_text_to_sql_views.sql` in the Supabase SQL Editor.

## Validation (2026-06-14)

| Check | Result |
|-------|--------|
| Backend unit tests (`pytest tests/`) | 39 passed |
| Frontend TypeScript (`tsc --noEmit`) | Pass |
| Build on branch `module-7-multi-tool-agent` | All plan cards committed |

**Manual E2E** (re-test when `DATABASE_URL`, `TAVILY_API_KEY`, or migrations change):

1. Document content → `search_documents` + source chips
2. Library count → `query_database` + SQL attribution
3. Online query → `web_search` + URL chips (with Tavily key)
4. SQL validator blocks `content` / raw `document_chunks`
5. RLS smoke test (two users)

See `PROGRESS.md` → Module 7 → **Re-test later**.