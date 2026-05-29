# Modules 4, 5, 6 — discussion

*Chat-style notes from our conversations. Not a plan doc — just what we talked through.*

---

**You:** What is Module 4 for?

**Us:** Module 4 is metadata extraction. At ingest, an LLM reads the document text and fills a fixed schema (title, type, date, topics, etc.). You store that on the document in Supabase. At chat time you can filter retrieval — “only policies from 2024” — before vector search runs. It helps when you have many docs and the wrong one is semantically close. It does not mean sending the full doc to the model.

---

**You:** How is metadata extracted — per chunk or per document?

**Us:** The course leans document-level: one LLM call per file, one JSON blob on `documents`. Chunk-level is optional later (section titles, page numbers) when one PDF mixes many topics. ChatGPT and NotebookLM feel document-centric in the UI (one file / one source) but cite passages — so chunks are for search and citations, metadata mostly labels the whole source.

**You:** What’s best?

**Us:** Default: document-level LLM metadata + chunking for retrieval. Add chunk-level or parser-derived fields (page, heading) when users say “right file, wrong paragraph.” Consumer apps don’t show you the JSON; they still chunk internally.

---

**You:** Forget Module 4 — I want a system that answers from lengthy docs without passing the whole doc to the LLM.

**Us:** That’s already the core RAG pattern, and your app does it today:

- **Ingest once:** full doc → chunks → embeddings → database.
- **Each question:** embed the question → find top similar chunks → only those go in the prompt.

The model never sees 500 pages at once; it sees a small set of excerpts plus chat history. Limits: retrieval can miss the right chunk; very broad questions (“summarize everything”) may need more chunks, multi-query, or map-reduce — still not one giant paste.

ChatGPT / NotebookLM: you see a file or source; behind the scenes it’s chunk + retrieve + cite passages. Same split you’d build: store whole doc, send only slices.

---

**You:** What is Module 4 vs the rest of the modules for a robust pipeline? Hybrid search and reranking?

**Us:** Quick map:

- **Done (1–3):** shell, RAG, record manager (hash, skip unchanged).
- **4:** which documents are even in the race (filters).
- **5:** better text from PDF/DOCX/HTML (docling) → better chunks.
- **6:** hybrid (keyword + vector, RRF) then rerank — biggest fix for “wrong passage” on long docs.
- **7–8 later:** web/SQL when docs don’t have it; sub-agents for heavy whole-doc work.

For “any question from long docs,” priority after 2–3 is roughly **6 → 5 → 4**. Module 6 doesn’t send more text; it picks better chunks. Module 4 helps big libraries; Module 6 helps almost every query.

---

**You:** We’ll do Modules 4, 5, and 6 in one go, built correctly together.

**Us:** Agreed — one delivery, not three separate releases. Same pipeline:

Upload → parse well (5) → extract metadata (4) → chunk → embed.  
Chat → optional metadata narrow (4) → hybrid retrieve (6) → rerank (6) → small context → LLM.

Recorded in `PROGRESS.md` under “Current focus: Modules 4 + 5 + 6.”

---

*Add new turns below as we keep discussing.*
