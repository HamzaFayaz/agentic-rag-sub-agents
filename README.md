# agentic-rag-sub-agents

A hands-on project for building a production-style RAG application with AI coding tools (Cursor, Claude Code, etc.). You learn RAG concepts and codebase structure while implementing features module by module—not by memorizing Python or React syntax.

**Status:** Planning only. No application code yet. See [PRD.md](./PRD.md) for the full product spec.

## What we're building

Two main interfaces:

1. **Chat** (default) — Threaded conversations with retrieval-augmented, streaming responses
2. **Ingestion** — Manual file upload (drag-and-drop), processing status, document management

Not included: automated connectors, scheduled ingestion, or an admin UI. Configuration is via environment variables.

## Stack (planned)

| Layer | Technology |
|-------|------------|
| Frontend | React, TypeScript, Vite, Tailwind, shadcn/ui |
| Backend | Python, FastAPI |
| Database | Supabase (Postgres, pgvector, Auth, Storage, Realtime) |
| LLM | OpenAI Responses API (Module 1), then OpenAI-compatible Chat Completions (Module 2+) |
| Observability | LangSmith |

## Learning path (modules)

| Module | Focus |
|--------|--------|
| 1 | App shell, auth, chat UI, OpenAI Responses API, LangSmith |
| 2 | BYO retrieval, ingestion, embeddings, pgvector, chat memory |
| 3 | Record manager (deduplication, incremental updates) |
| 4 | Metadata extraction and filtered retrieval |
| 5 | Multi-format docs (PDF, DOCX, HTML, Markdown) |
| 6 | Hybrid search and reranking |
| 7 | Text-to-SQL and web search fallback |
| 8 | Sub-agents with isolated context |

## Capabilities (when complete)

- Document ingestion, vector + hybrid search, reranking
- Multi-format documents, metadata extraction, record management
- Text-to-SQL and web search tools
- Sub-agents, threaded chat, streaming (SSE), auth with RLS

## Getting started

Implementation has not started. When Module 1 lands, setup instructions (env vars, Supabase, local dev) will go here.

For scope, constraints, and architectural decisions (e.g. Module 1 → Module 2 transition), read **[PRD.md](./PRD.md)**.
