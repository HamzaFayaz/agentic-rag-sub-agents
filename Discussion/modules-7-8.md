# Modules 7, 8 — discussion

*Chat-style notes from our conversations. Not a plan doc — just what we talked through.*

**Module 7 status:** Complete & validated (2026-06-14). See `PROGRESS.md` and `Discussion/module-7-tool-routing-flow.md`.

---

## Module 7 — what it is (two parts)

**Module 7 = multi-tool agent.** Today every chat message always runs RAG first. Module 7 replaces that with an **LLM tool-calling loop** — the model picks the right tool per question.

| Part | Tool name (planned) | What it does |
|------|---------------------|--------------|
| **1 — Document RAG (existing, wrapped as tool)** | `search_documents` | Hybrid search over `document_chunks.content` — everything Modules 2–6 already do |
| **2 — Text-to-SQL (new)** | `query_database` | LLM writes a read-only `SELECT`, backend validates + runs it on Postgres, returns table rows |
| **3 — Web search (new)** | `web_search` | External search when docs/DB don't have the answer — you already know this one |

**Also changes in Module 7 (not separate “parts” but required):**

- Chat loop refactor — OpenAI function calling instead of always-on `RetrievalService.retrieve()`
- SSE events — `tool_start` / `tool_end` so UI shows which tool ran
- Attribution — doc citations (existing), SQL query shown in UI, web URLs cited
- LangSmith spans per tool
- Env flags — `TEXT_TO_SQL_ENABLED`, `WEB_SEARCH_ENABLED`, etc.

**Status:** Not built yet. Modules 1–6 complete; Module 7 is next.

---

**You:** I get web search — when docs don't have the answer. What is Text-to-SQL for? Why do we need it in a RAG app?

**Us:** Short answer: **RAG reads prose inside documents. Text-to-SQL answers questions about your database rows — counts, lists, filters, sorts — that RAG cannot do reliably.**

---

### The problem RAG cannot solve

Modules 2–6 built a **document retrieval** pipeline:

```text
Upload → parse (M5) → metadata (M4) → chunk → embed → store in document_chunks
Chat   → embed question → hybrid + rerank (M6) → top text chunks → LLM answer
```

That is great for: *"What does our handbook say about sick leave?"* — find the right **passage** and quote it.

It is **bad** for:

- *"How many documents have I uploaded?"*
- *"List all PDFs I uploaded in March"*
- *"Which file has the most chunks?"*
- *"Do I have more policies or contracts?"*

**Why?** RAG searches **semantic similarity on chunk text**. It might retrieve a random chunk that mentions "policy" and guess wrong. It cannot run `COUNT(*)`, `GROUP BY`, or `ORDER BY created_at`. Those need **SQL on structured rows**.

---

### What Text-to-SQL actually is (in this app)

**Text-to-SQL = a tool where:**

1. User asks a question in plain English
2. LLM generates a `SELECT` query (only `SELECT`, no writes)
3. Your backend **validates** it (allowlist tables/views, row cap, RLS)
4. Postgres runs it **as the logged-in user** (same RLS as today)
5. Table results go back to the LLM → final answer

You are **not** building a generic BI tool or connecting to a sales ERP. In this codebase, SQL targets **your existing Supabase tables** — the same data you already own from Modules 1–6.

---

### Two different data types in your app

| Data type | Lives in | Example questions | Right tool |
|-----------|----------|-------------------|------------|
| **Unstructured** — document prose | `document_chunks.content` | "What skills are on Hamza's CV?" | **RAG** (`search_documents`) |
| **Structured** — rows and columns | `documents`, `document_chunks` (metadata columns), `threads`, `messages` | "How many docs?", "largest file?" | **Text-to-SQL** (`query_database`) |
| **External** — not in your DB | — | "Latest GDPR news?" | **Web search** |

**One line:** `documents` + chunk **columns** = SQL. `document_chunks.content` = RAG.

---

### Concrete examples (this codebase)

With tables you already have plus Module 4 metadata on `documents.metadata`:

| User question | Wrong tool | Right tool |
|---------------|------------|------------|
| "How many documents have I uploaded?" | RAG (might find a chunk mentioning uploads) | **SQL** `COUNT(*) FROM documents WHERE user_id = …` |
| "How many are still processing?" | RAG | **SQL** `WHERE status = 'processing'` |
| "List my policy documents" | RAG (semantic guess) | **SQL** `WHERE metadata->'llm'->>'doc_type' = 'policy'` |
| "Which file is largest?" | RAG | **SQL** `ORDER BY byte_size DESC LIMIT 5` |
| "How many chunks does my CV have?" | RAG (one random chunk) | **SQL** join `documents` + `document_chunks`, `COUNT` |
| "What topics appear most in my library?" | RAG | **SQL** on `metadata->'llm'->'topics'` |
| "What does the handbook say about sick leave?" | **RAG** | SQL ❌ — need passage text |
| "What's the latest GDPR update?" | **Web search** | SQL ❌ — not in your DB |

**Pattern:** if the answer is a **number, list, filter, sort, or aggregate** over rows you own → SQL. If the answer is **inside document prose** → RAG. If **neither** → web.

---

### Why not just use Module 4 metadata instead of SQL?

Module 4 stores tags (`doc_type`, `topics`, `summary`) in `documents.metadata.llm`. That helps **label** documents at ingest. It does **not** replace SQL:

- **M4** = tags on each document (good for display and future filters)
- **SQL** = precise **counts and comparisons** across those rows

Example: *"Do I have more policies or contracts?"*

- Metadata alone can't compare counts — you need `GROUP BY doc_type`
- RAG might retrieve chunks from both types and **hallucinate** a ratio

Module 4 and Text-to-SQL **complement** each other: M4 labels documents; M7 SQL **queries** those labels.

---

### What tables would the SQL tool query?

Not a fake sales database. For this course, natural targets:

**`documents`** — filename, status, mime_type, byte_size, created_at, `metadata` jsonb (Module 4 + 5)

**`document_chunks`** — count per document, `section_title`, `chunk_index` (Module 5 structure) — **not** `content` for aggregates

**Optionally** `threads`, `messages` — "how many chats this week?"

**Safety (required):**

- SELECT only — read-only role
- Allowlist tables/views
- RLS — user only sees their rows
- Row cap (e.g. max 100)
- Show generated SQL in UI for trust

**Recommended v1:** read-only views like `v_user_document_stats` so the LLM only sees safe relations.

---

### How Module 7 fits the architecture

**Today:**

```text
User message → always RetrievalService.retrieve() → RAG prompt → LLM
```

**After Module 7:**

```text
                    ┌─ search_documents (hybrid RAG, M2–M6)
User question → LLM ─┼─ query_database (Text-to-SQL)     ← NEW
                    └─ web_search (external)             ← NEW
```

PRD learning goal: **routing between structured and unstructured data** — the agent picks the tool, not always vector search.

---

### One sentence each — Module 7 tools

- **Document RAG:** find the right **passages** in uploaded files.
- **Text-to-SQL:** get exact **numbers and lists** from your database — how many docs, which type, largest file, chunk counts, metadata aggregates.
- **Web search:** when **neither docs nor DB** have the answer.

**Module 7 teaches:** don't force every question through vector search; route structured vs unstructured vs external, and show where the answer came from.

---

## Module 8 — preview (not discussed yet)

**Module 8 = sub-agents** — detect full-document tasks, spawn isolated sub-agent with its own tools, nested tool UI. Separate from Module 7.

---

*Add new turns below as we keep discussing.*
