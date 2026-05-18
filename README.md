# agentic-rag-sub-agents

Production-oriented RAG application with a chat interface and a document ingestion pipeline. Users upload files manually, query their knowledge base with streaming answers, and rely on hybrid retrieval, tool use, and sub-agents for complex questions.

**Status:** In planning — application code not started yet.

## Overview

Full-stack agentic RAG system: threaded chat with retrieval-augmented generation, plus an ingestion UI for upload, processing status, and document management. Auth and row-level security ensure each user only accesses their own data. Configuration is environment-based (no admin panel).

## Features

- **Chat** — Multi-turn threads, streaming responses (SSE), conversation memory
- **Ingestion** — Drag-and-drop upload, processing tracking, document lifecycle management
- **Retrieval** — Vector search (pgvector), hybrid keyword + vector search, reranking
- **Documents** — PDF, DOCX, HTML, Markdown; chunking, embeddings, deduplication via content hashing
- **Metadata** — LLM-based structured extraction and metadata-filtered retrieval
- **Tools** — Text-to-SQL for structured data; web search when documents are insufficient
- **Agents** — Sub-agents with isolated context for full-document and delegated tasks
- **Platform** — Supabase auth with RLS, realtime ingestion status, LangSmith observability

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | React, TypeScript, Vite, Tailwind, shadcn/ui |
| Backend | Python, FastAPI |
| Database | Supabase (Postgres, pgvector, Auth, Storage, Realtime) |
| LLM | OpenAI-compatible Chat Completions API |
| Observability | LangSmith |
