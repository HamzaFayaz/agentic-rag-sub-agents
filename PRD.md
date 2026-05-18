# agentic-rag-sub-agents - PRD

## What We're Building

A RAG application with two interfaces:
1. **Chat** (default view) - Threaded conversations with retrieval-augmented responses
2. **Ingestion** - Upload files manually, track processing, manage documents

This is **not** an automated pipeline with connectors. Files are uploaded manually via drag-and-drop. Configuration is via environment variables, no admin UI.

## Target Users

Technically-minded people who want to build production RAG systems using AI coding tools (Claude Code, Cursor, etc.). They don't need to know Python or React - that's the AI's job.

**They need to understand:**
- RAG concepts deeply (chunking, embeddings, retrieval, reranking)
- Codebase structure (what sits where, how pieces connect)
- How to direct AI to build what they need
- How to direct AI to fix things when they break

## Scope

### In Scope
- ✅ Document ingestion and processing
- ✅ Vector search with pgvector
- ✅ Hybrid search (keyword + vector)
- ✅ Reranking
- ✅ Metadata extraction
- ✅ Record management (deduplication)
- ✅ Multi-format support (PDF, DOCX, HTML, Markdown)
- ✅ Text-to-SQL tool
- ✅ Web search fallback
- ✅ Sub-agents with isolated context
- ✅ Chat with threads and memory
- ✅ Streaming responses
- ✅ Auth with RLS

### Out of Scope
- ❌ Knowledge graphs / GraphRAG
- ❌ Code execution / sandboxing
- ❌ Image/audio/video processing
- ❌ Fine-tuning
- ❌ Multi-tenant admin features
- ❌ Billing/payments
- ❌ Data connectors (Google Drive, SFTP, APIs, webhooks)
- ❌ Scheduled/automated ingestion
- ❌ Admin UI (config via env vars)

## Stack

| Layer | Choice |
|-------|--------|
| Frontend | React + TypeScript + Vite + Tailwind + shadcn/ui |
| Backend | Python + FastAPI |
| Database | Supabase (Postgres + pgvector + Auth + Storage + Realtime) |
| LLM (all modules) | OpenAI-compatible Chat Completions API (OpenAI, OpenRouter, Ollama, LM Studio, etc.) |
| Chat memory | Supabase (threads + messages); stateless API — load history and send each request |
| Observability | LangSmith |

## Constraints

- No LLM frameworks - raw OpenAI SDK using the standard Chat Completions API (OpenAI-compatible), Pydantic for structured outputs
- Row-Level Security on all tables - users only see their own data
- Streaming chat via SSE
- Ingestion status via Supabase Realtime

---

## Module 1: The App Shell + Observability

**Build:** Auth, threaded chat UI, Supabase-backed conversation history, stateless Chat Completions API (streaming via SSE), LangSmith tracing

**Out of scope for Module 1:** RAG, document upload/ingestion, OpenAI managed `file_search`, Responses API, pgvector retrieval

**Chat flow (you own memory, not OpenAI):**
1. User sends a message in a thread
2. Backend loads prior messages for that thread from Supabase
3. Backend calls Chat Completions with `system` + history + new user message
4. Assistant reply is streamed to the UI and saved to Supabase
5. Next turn repeats with the updated history

**Learn:** Full-stack app shell, Supabase auth + RLS, stateless LLM APIs, storing and resending chat history, SSE streaming, observability from day one

**Note:** Module 1 is LLM chat only. The same Chat Completions + Supabase history pattern continues in Module 2 when RAG is added on top.

---

## Module 2: BYO Retrieval + RAG

**Prerequisites:** Module 1 complete (auth, chat UI, threads/messages in Supabase, streaming Chat Completions).

**Build:** Ingestion UI, file storage, chunking → embedding → pgvector, retrieval tool wired into the existing chat flow, realtime ingestion status

**Learn:** Chunking, embeddings, vector search, tool calling, relevance thresholds, injecting retrieved context into Chat Completions requests

---

## Module 3: Record Manager

**Build:** Content hashing, detect changes, only process what's new/modified

**Learn:** Why naive ingestion duplicates, incremental updates

---

## Module 4: Metadata Extraction

**Build:** LLM extracts structured metadata, filter retrieval by metadata

**Learn:** Structured extraction, schema design, metadata-enhanced retrieval

---

## Module 5: Multi-Format Support

**Build:** PDF/DOCX/HTML/Markdown via docling, cascade deletes

**Learn:** Document parsing challenges, format considerations

---

## Module 6: Hybrid Search & Reranking

**Build:** Keyword + vector search, RRF combination, reranking

**Learn:** Why vector alone isn't enough, hybrid strategies, reranking

---

## Module 7: Additional Tools

**Build:** Text-to-SQL tool (query structured data), web search fallback (when docs don't have the answer)

**Learn:** Multi-tool agents, routing between structured/unstructured data, graceful fallbacks, attribution for trust

---

## Module 8: Sub-Agents

**Build:** Detect full-document scenarios, spawn isolated sub-agent with its own tools, nested tool call display in UI, show reasoning from both main agent and sub-agents

**Learn:** Context management, agent delegation, hierarchical agent display, when to isolate

---

## Success Criteria

By the end, students should have:
- ✅ A working RAG application they built with AI assistance
- ✅ Deep understanding of RAG concepts (chunking, embedding, retrieval, reranking)
- ✅ Understanding of codebase structure - what lives where, how pieces connect
- ✅ Ability to direct AI coding tools to build new features
- ✅ Ability to direct AI coding tools to debug and fix issues
- ✅ Experience with agentic patterns (multi-tool, sub-agents)
- ✅ Observability set up from day one
