# Release v5 — Module 8: Document Analyst Sub-Agent

**Status:** Complete & validated (2026-06-25). Tagged as **v5** on `main` (from branch `module-8-sub-agents`).

## Summary

Module 8 adds **`analyze_document`** — an isolated document analyst sub-agent for whole-document summaries, deep reads, and compare-two-files tasks. The main agent keeps `search_documents`, `query_database`, and `web_search`. The sub-agent does not get those tools.

## Token-aware routing

| Condition | Mode | Behavior |
|-----------|------|----------|
| `total_token_count <= SUB_AGENT_CONTEXT_TOKEN_BUDGET` | `single_pass` | Stitch chunks → one LLM call |
| Larger document | `multi_pass` | Batch chunks, map running notes, final reduce report |

Internal map batches are capped by `SUB_AGENT_INTERNAL_MAX_PASSES` (default 8). Output is a compact report (~`SUB_AGENT_OUTPUT_MAX_TOKENS`, default 2000) — never the full document.

## Per-turn cap

`SUB_AGENT_MAX_PER_TURN=2` (ceiling, not default):

- Most turns: no sub-agent (RAG handles normal questions)
- Whole-document task: 1 analysis
- Compare two files: 2 analyses
- 3rd `analyze_document` call in one turn → tool error

## Tool boundary

| Use | Tool |
|-----|------|
| Pinpoint facts, excerpts | `search_documents` |
| Whole doc / deep read / compare | `analyze_document` |
| Library counts, lists, filters | `query_database` |
| Online / current events | `web_search` |

## UI & SSE

- `tool_start` / `tool_end` for `analyze_document` (same as other tools)
- `subagent_progress` events: `{pass, total_passes, mode, filename}`
- ChatGPT-style vertical step list (e.g. `Calling sub-agent to read and analyze handbook.pdf`)
- Assistant replies render **markdown** (headings, lists, bold)
- **Parallel compare:** when the model calls `analyze_document` twice in one step, both sub-agents run concurrently

## Configuration

See `.env.example`:

- `SUB_AGENT_ENABLED` (default `true`)
- `SUB_AGENT_MAX_PER_TURN` (default `2`)
- `SUB_AGENT_CONTEXT_TOKEN_BUDGET` (default `80000`)
- `SUB_AGENT_INTERNAL_MAX_PASSES` (default `8`)
- `SUB_AGENT_OUTPUT_MAX_TOKENS` (default `2000`)
- `SUB_AGENT_MODEL` (default `gpt-4o-mini`)

## Migration

Apply `supabase/migrations/008_document_token_count.sql` in the Supabase SQL Editor.

**Note:** `total_token_count` must be appended **after** `chunk_count` in `v_user_document_stats` — Postgres `CREATE OR REPLACE VIEW` cannot insert columns mid-list.

## LangSmith

New spans: `document_analyze` (parent) and `document_analyze_pass` (per internal LLM call).

## Validation (2026-06-25)

| Check | Result |
|-------|--------|
| `test_sub_agent.py` — budget, batching, analyst, cap, RLS, parallel grouping | Pass |
| `test_tool_dispatcher.py` — `analyze_document` gate + dispatch | Pass |
| Full backend `pytest` | 52 passed |
| Frontend TypeScript (`tsc --noEmit`) | Pass |
| Docs: README, PROGRESS, RELEASE_v5 | Updated |

**Manual E2E** (re-test when migrations or sub-agent config change):

1. Summarize whole handbook → single or multi pass + progress chip
2. Compare two contracts → 2 analyses
3. Fact question → `search_documents` only
4. 3rd analyze in one turn → blocked
5. Unknown filename → error with available files
6. RLS: User B cannot analyze User A's document
7. `SUB_AGENT_ENABLED=false` → tool omitted

See `PROGRESS.md` → Module 8 → **Re-test later**.
