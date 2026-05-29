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

**You:** Is there a better approach than Module 4 when we ship 5 and 6 together? Results + token cost. Product-grade — client can’t get a mess at this stage.

**Us:** Yes — treat Module 4 as **thin and cheap**, and let **5 + 6 carry most of the quality**. Don’t run a big model (Opus, etc.) on every upload for metadata. Your app already defaults to `gpt-4o-mini` for chat — use the same tier (or smaller) for extraction, never the “best” model for background ingest.

**What actually moves the needle for answers on long docs**

Module 6 (hybrid + rerank) fixes “found the wrong paragraph” — that’s most user-visible quality. Module 5 fixes “chunks are garbage because PDF text sucked” — without good text, vectors and keywords both fail. Module 4 helps most when someone has **lots of similar documents** and you need to exclude the wrong file. If the library is small, M4 matters less.

So for product grade in one release: **5 and 6 are non-negotiable core; 4 is a small, safe add-on** — not the star of the show.

**Better than “classic Module 4” (full LLM read of every doc)**

Use a **two-layer metadata** approach — still one pipeline, less mess, fewer tokens:

1. **Free layer (from Module 5 parsing)** — no LLM: filename, mime, page count, section headings from doc structure, language guess if parser gives it. Store on `documents.metadata` or sibling columns. This already improves chunking and UI and costs zero tokens.

2. **Cheap LLM layer (slim Module 4)** — one short structured call per **new/changed** file only (Module 3 `unchanged` skips it): small schema (title, doc_type, 3–5 topics, one-line summary). For huge files, don’t send the whole book — send **first N chars + outline/headings** from the parser. Fail open: if extraction fails, ingest still completes with `metadata: null`.

3. **Do not** use LLM metadata on every chunk — token burn with little gain for v1.

**Chat time — keep it cheap**

- Retrieval: hybrid → rerank → **same small top-K** into the prompt (you already cap context).
- **Don’t** call a big model on every question just to guess metadata filters at first — adds latency and cost. Add “smart filters from the question” later if needed; start with optional UI filters or none.
- Reranking: prefer a **dedicated rerank API** (e.g. Cohere rerank, or similar) over asking a chat model to score 30 chunks — better quality per dollar than Opus-style reranking.

**Token / cost rules of thumb (client-safe)**

| Step | Cost profile | Rule |
|------|----------------|------|
| Parse (M5) | CPU / docling | No LLM |
| Metadata (M4) | 1 small call per changed file | Skip if `unchanged`; truncate huge docs |
| Embed | per chunk | Unchanged doc = skip entirely (M3) |
| Hybrid (M6) | DB / FTS + vector | Cheap |
| Rerank (M6) | rerank API on ~20–30 hits | Not 100; not Opus |
| Answer | mini + 5 chunks | Don’t raise K “just because” |

**Will results improve if we still do Module 4?**

Yes, but **incrementally** and mostly for multi-doc libraries. **5 + 6 improve almost every query.** Combined: good text (5) → good candidates (hybrid) → good final slices (rerank) → optional doc-level tags (4) when many files overlap. That’s the product story — not “we added Opus at ingest.”

**How not to make a mess for the client**

- Ingest never blocked on metadata failure.
- One retrieval path: always hybrid + rerank in prod; no half-migrated vector-only branch left on.
- Env flags: `METADATA_EXTRACTION_ENABLED`, rerank on/off for debugging.
- Same chat model family as today; document what runs where in README.
- Ship behavior: upload still works like today; chat gets better retrieval; metadata is visible but filters can be phase 2.

**Bottom line:** For a product-grade 4+5+6 drop, the better approach is **M5 parsing quality + M6 hybrid/rerank as the quality engine**, and **M4 as lightweight document tags** (parser facts + one cheap structured call), not a heavy “read the entire doc with the best model” step. That keeps cost predictable and avoids the stage where ingest becomes slow, expensive, and flaky — the kind of thing that gets you killed. 😛

---

**You:** Explain the two-layer metadata approach more clearly — free layer vs second layer, what we get, how it works. Is this standard and will it work?

**Us:** Yes — this is a **standard production pattern**. Lots of teams do **parser/structural metadata (free)** plus **optional LLM enrichment (paid)**. You’re not inventing something weird; you’re avoiding “one expensive LLM read of the whole PDF” as the only source of truth.

---

### Layer 1 — Free metadata (from Module 5 parsing, no LLM)

**How it works**

When a file is uploaded, **docling** (or similar) turns the file into clean text **and** structure. Your code walks that output and **records facts in code** — no API call, no tokens.

**What you typically get**

| Field | Where it comes from | Example |
|-------|---------------------|---------|
| `filename` | Upload | `hr-policy-2024.pdf` |
| `mime_type` / extension | Upload | `application/pdf`, `.docx` |
| `byte_size` | Upload | `2_400_000` |
| `page_count` | PDF parser | `48` |
| `language` | Parser detector (if available) | `en` |
| `headings` | Document outline | `["1. Introduction", "2. Leave", "3. Termination"]` |
| `sections` | Chunks tied to heading + page | `{ "title": "2. Leave", "page_start": 5, "page_end": 7, "text": "..." }` |
| `title_guess` | First H1 or document title property | `Employee Handbook 2024` |
| `parsed_at` | Your server clock | ISO timestamp |

**Stored where**

Usually `documents.metadata` jsonb, e.g.:

```json
{
  "source": "parser",
  "page_count": 48,
  "headings": ["1. Introduction", "2. Leave", "3. Termination"],
  "title_guess": "Employee Handbook 2024",
  "language": "en"
}
```

Optional: copy `page` / `section_title` onto each **chunk row** when you split — still free, helps citations (“page 12, section Refunds”).

**What it’s good for**

- Better **chunking** (split on headings, not blind 600-char windows).
- UI: show page count, doc title, outline on Documents page.
- Light **filters** without LLM: “only PDFs”, “docs with heading containing Leave”.
- Hybrid search (Module 6) works better because **keyword search** hits real words from a clean parse.

**What it cannot do**

- Understand “this is a legal contract vs marketing blog” unless the heading says so.
- Infer topics that are never written explicitly.
- Paraphrase or summarize — that needs Layer 2 or the user’s question at chat time.

---

### Layer 2 — Cheap LLM metadata (slim Module 4, small token cost)

**How it works**

After Layer 1, you have clean text (and maybe headings). You send a **short, fixed prompt** to a **small chat model** (`gpt-4o-mini` class) with **structured output** (Pydantic → JSON). **One call per document**, only when the file is **new or content changed** (Module 3 `unchanged` → skip entirely).

**What you send (keep input small)**

- Filename  
- Layer 1: `title_guess`, `headings`, `page_count`  
- Text sample: e.g. first ~8k characters **or** concatenated section intros — **not** a 300-page paste  

**What you get back (small schema)**

| Field | Meaning |
|-------|---------|
| `title` | Human-readable doc title |
| `doc_type` | `policy`, `contract`, `report`, `manual`, `other` |
| `topics` | 3–5 tags, e.g. `["HR", "leave", "termination"]` |
| `summary` | 1–2 sentences |
| `date_guess` | Best-effort date or `null` |
| `entities` | Optional: org names, products (keep short) |

**Stored where**

Merge into same `documents.metadata`, tagged so you know the source:

```json
{
  "source": "parser",
  "page_count": 48,
  "headings": ["..."],
  "llm": {
    "title": "Employee Handbook",
    "doc_type": "policy",
    "topics": ["HR", "leave"],
    "summary": "Covers leave, conduct, and termination for all staff.",
    "date_guess": "2024-01-01"
  }
}
```

**What it’s good for**

- Filtering when the library is large: “policies about leave from 2024”.
- Documents list: tags and summary without opening the file.
- Narrowing vector/hybrid search to the right **files** before chunk search.

**What it’s not**

- Not run on every chunk.
- Not run on every chat message (unless you add that later).
- Not allowed to block ingest — if the LLM fails, Layer 1 metadata still saves and doc goes `ready`.

---

### How the two layers work together at runtime

```text
INGEST
  file → Parser (Layer 1 facts + good text)
       → optional LLM (Layer 2 tags)  [skip if unchanged]
       → chunk (use headings/pages if you can)
       → embed → store

CHAT
  question → hybrid + rerank on CHUNKS (Module 6)   ← main quality
          → optional: filter documents where metadata.llm.doc_type = 'policy'
          → top chunks → small prompt → answer
```

Layer 1 improves **what gets chunked and searched**.  
Layer 2 improves **which documents enter the search**.  
Module 6 improves **which chunks win** inside those docs.

---

### Is this standard? Will it work?

**Standard:** Yes. Common names for the same idea:

- **Structural / document metadata** (Layer 1) — from parsers, CMS, file properties.  
- **Semantic / enriched metadata** (Layer 2) — from LLM or human tags.  

Enterprises often skip Layer 2 at first and still ship; add Layer 2 when the doc count grows.

**Will it work:** Yes, for product RAG, if you respect:

1. Layer 1 is reliable when parsing is reliable (Module 5 matters).  
2. Layer 2 is **best-effort** — never required for ingest to succeed.  
3. **Retrieval quality** still depends on hybrid + rerank (Module 6), not metadata alone.  
4. Re-upload unchanged = no Layer 2 call (cost control).

**Risk to avoid:** Using only Layer 2 and skipping Layer 1 — you pay tokens and still get bad chunks from a bad PDF parse. That’s the “mess” path. **Parser first, LLM second** is the safe order.

---

**You:** Layer 1 and Layer 2 fields look like some are repeating — title vs title_guess, headings vs topics, etc.

**Us:** Good catch. A few fields **sound** similar but they are **not duplicates** if you treat them differently. Some teams **drop** a Layer 2 field when Layer 1 is already good enough.

**Side-by-side — what repeats vs what doesn’t**

| Looks similar | Layer 1 | Layer 2 | Same thing? |
|---------------|---------|---------|-------------|
| Title | `title_guess` — literal from doc (H1, PDF title metadata) | `title` — cleaned / normalized label | **Related, not duplicate.** Guess can be wrong or ugly (`Document1`); LLM can fix spelling and shorten. **Rule:** show `llm.title` in UI if present, else `title_guess`. |
| Topics vs outline | `headings` — exact strings from the file | `topics` — inferred tags | **Different.** Headings = table of contents. Topics = “what is this about?” (e.g. heading says `3.2 ACME` but topic is `termination`). Keep both. |
| Summary | — | `summary` | **L2 only.** No repeat. |
| Type of doc | mime / extension (`.pdf`) | `doc_type` (`policy`, `contract`) | **Different.** MIME = file format. `doc_type` = meaning. No repeat. |
| Date | `parsed_at` = when *you* indexed it | `date_guess` = when doc claims to be from | **Different.** Don’t confuse them. |
| Sections | `sections` (heading + page + text slice) | — | **L1 only.** Used for chunking/citations, not LLM. |
| Entities | — | `entities` (orgs, products) | **L2 only.** Parser usually doesn’t give this reliably. |
| Language | `language` from detector | — | **L1 only** unless you want LLM to double-check (usually skip). |
| Filename, byte_size, page_count | L1 only | — | No repeat. |

**What is actually redundant (and what to do)**

1. **`title_guess` + `llm.title`** — Only redundant when they agree. **Do:** store both under clear keys; UI picks `llm.title` ?? `title_guess`. Optional: skip LLM `title` if `title_guess` is already long and clean (save tokens).

2. **`headings` + `topics`** — Not redundant; don’t merge into one list. Headings for structure; topics for search filters.

3. **`summary`** — Could overlap *content* with first heading + intro, but summary is for humans/filters; headings are not a summary. Keep summary in L2 only.

**Slim schema if you want zero “feel” of repetition**

**Layer 1 (parser only)** — facts you can measure:

`filename`, `mime_type`, `byte_size`, `page_count`, `language`, `headings`, `sections`, `parsed_at`

Optional: `title_guess` only if parser found a real title.

**Layer 2 (LLM only)** — things parser cannot know:

`doc_type`, `topics`, `summary`, `date_guess`, `entities`

**Drop `title` from Layer 2** if `title_guess` is good — let LLM fill title only when guess is empty or generic (`Untitled`, `Document1`).

That gives you **no overlapping field names** and lower token use, while keeping the two-layer idea intact.

**One jsonb shape (no duplicate keys)**

```json
{
  "parser": {
    "page_count": 48,
    "language": "en",
    "headings": ["1. Introduction", "2. Leave"],
    "title_guess": "Employee Handbook 2024",
    "parsed_at": "2026-05-29T12:00:00Z"
  },
  "llm": {
    "doc_type": "policy",
    "topics": ["HR", "leave", "termination"],
    "summary": "Staff policies for leave and conduct.",
    "date_guess": "2024-01-01",
    "entities": ["ACME Corp"]
  }
}
```

`filename` / `mime_type` / `byte_size` stay as normal **columns** on `documents` (you already have most of these) — no need to duplicate them inside `metadata`.

**Bottom line:** repetition is mostly **title** and partly **conceptual** (headings vs topics). Split **parser.*** vs **llm.*** namespaces, drop LLM `title` when guess is fine, and you’re aligned with a standard, non-messy schema.

---

**You:** Heading-based chunking sounds good, but what about parent–child / hierarchical chunks? Users can upload any file type and structure. How do we solve that?

**Us:** You don’t pick **one** strategy forever. You use **adaptive chunking**: try structure first, fall back when there is none, and optionally add **parent–child** for long or messy docs.

---

### The problem

| Document | Headings? | Heading-only chunking |
|----------|-----------|------------------------|
| Well-formed PDF/DOCX with H1/H2 | Yes | Works well |
| Plain `.txt` pasted notes | No | Falls apart |
| Scanned PDF, tables, slides | Weak / none | Bad splits |
| One giant section (50 pages under one H1) | Yes but useless | One huge “chunk” |

So: **heading-based is the default when structure exists**, not the only path.

---

### Strategy: three paths after Module 5 parse

```text
Parse file (docling) → detect structure quality
  ├─ A) Good outline → section/heading chunks
  ├─ B) Weak/no outline → fixed-size + overlap (what you have today)
  └─ C) Huge section or long doc → parent–child inside A or B
```

**How you detect “good outline” (simple rules, no LLM)**

- At least N headings (e.g. 2+), or
- Headings cover ≥ X% of pages/lines, or
- Max section length under your cap

Else → **fallback path B**.

---

### Path A — Heading / section chunks (primary)

- Split on parser headings (H1/H2/…).
- Each section = one or more **child** chunks if still too long (split with overlap inside that section only).
- Store on chunk: `section_title`, `page_start`, `heading_level`.

---

### Path B — Fallback (no structure)

- Same as today: `chunk_size` + `chunk_overlap` on full text.
- Store `section_title: null` so retrieval/UI stay consistent.
- Still works for any upload; quality is “OK,” not optimal.

---

### Path C — Parent–child / hierarchical (when you need it)

**Idea**

- **Child** = small chunk (400–800 tokens) → **embedded & searched** (precise hit).
- **Parent** = larger block (whole section or 2–4 children merged) → **not always embedded**; loaded at answer time when a child matches.

**When to use**

- Section longer than max chunk size.
- User questions need surrounding context (child hit is one paragraph; parent is full “2. Leave” section).
- Optional for v1; add when you see “right snippet, missing context” in testing.

**Flow at chat time**

1. Hybrid + rerank finds **child** chunks.  
2. For each hit, fetch **parent** text (same `parent_id` or `section_id`).  
3. Send parent (or parent summary) + matched child to LLM — still not the full doc.

**DB sketch**

- `document_chunks`: `id`, `parent_id` (nullable), `chunk_level` (`child` | `parent`), `section_title`, `content`, `embedding` (usually on **child** only; parent optional).

---

### Any file type — what Module 5 actually guarantees

Module 5 does **not** mean “every file has perfect headings.” It means:

- PDF/DOCX/HTML/MD → **best-effort text + outline** from docling.
- Parser fails or empty → clear `failed` status (don’t silently index garbage).
- `.txt` with no `#` headers → path **B** automatically.

**One ingest pipeline, multiple chunk strategies** — chosen in code after parse, not chosen by the user.

---

### What we’re **not** doing in v1 (avoid mess)

- Full tree of arbitrary depth for every doc (overkill).
- LLM-decided chunk boundaries on every upload (cost + flaky).
- Different user-facing modes (“pick hierarchical”) — system decides from parse result.

---

### Recommended product order (4 + 5 + 6)

1. **M5 parse** + structure detection  
2. **Heading chunks + fallback** (A + B) — ship this first  
3. **M4 slim LLM metadata** on parser sample  
4. **M6 hybrid + rerank** on child chunks  
5. **Parent–child (C)** only if tests show context gaps  

**Bottom line:** Heading-based is the **preferred** path when structure exists; **fallback** handles chaos; **parent–child** fixes “small hit, need surrounding section” on long docs. Together that covers “any file, any structure” without pretending every upload is a neat handbook.

---

**You:** What if we pass docling info to the LLM and it suggests a chunking method? Worried we’ll need endless chunking code for strategies we didn’t build.

**Us:** Your worry is correct. **Open-ended “LLM pick any strategy” does not scale** — you become a slave to whatever the model invents (`semantic_blocks`, `table_aware`, `slide_per_page`, …) and you can’t ship reliably.

**Do not do:** “LLM returns free-text chunking plan → we try to implement it.”

**Do instead (product-safe):**

### Option 1 — No LLM for chunking (recommended v1)

Docling gives signals → **your code** picks from a **fixed enum** with rules:

- `SECTION` — good headings  
- `FIXED` — no structure  
- `PARENT_CHILD` — long sections (optional v1.1)  

Three implementations, one `if/elif`. Predictable, testable, no extra tokens.

### Option 2 — LLM only **classifies** into your enum (closed set)

Send docling **summary** (not full doc): page count, heading count, max section length, has tables?, mime type.

LLM returns **one of**:

```json
{ "strategy": "SECTION" | "FIXED" | "PARENT_CHILD" }
```

You still run **your** chunker for that strategy. If the model says something else → default `FIXED`.

- Small token cost (one short call).  
- Still only 3 code paths — **no infinite chunking modes**.

### Option 3 — LLM suggests **parameters**, not new algorithms

Same enum, plus allowed knobs only:

```json
{ "strategy": "SECTION", "max_chunk_tokens": 800, "overlap": 120 }
```

Bounded — you don’t add new chunkers, you tune existing ones.

---

**Why full “LLM designs chunking” fails for your client**

| Issue | Effect |
|-------|--------|
| Unbounded suggestions | New code every week |
| Hard to test | Same file, different strategy each run |
| Cost | Extra LLM call on every upload |
| Failure mode | Model hallucinates `strategy: legal_clause` → you have nothing |
| Debug | “Why did it chunk weird?” — opaque |

**What docling + LLM is good for**

- **Layer 2 metadata** (topics, doc_type) — closed schema.  
- **Optional** closed-set `strategy` enum — if rules aren’t enough.  
- **Not** inventing chunking algorithms.

**Practical rule**

> **You own chunking code. LLM may only choose a label from a menu you already built.**

Start with **Option 1** (rules from docling). Add **Option 2** only if real files keep landing in the wrong path after you tune rules.

---

**You:** How does parent–child chunking work? Is it hierarchical if there are only two levels? Is 2-level or 3-level hierarchy best — or parent–child?

**Us:** **Parent–child is hierarchical chunking with exactly 2 levels.** “3-level hierarchy” adds one more layer above parent (e.g. whole document → chapter → paragraph). Most products start with **2 levels**; add a third only for very long, deeply structured books.

---

### How parent–child works (2 levels)

**Level 1 — Parent (big context, weak or no search)**  
- Often a **full section** under one heading (e.g. entire “2. Leave policy”).  
- Stored in DB with `chunk_level = parent` (or `parent_id` null).  
- **Usually not embedded** (or embedded separately if you want “broad” search — optional).  
- Purpose: give the LLM **surrounding context** when a small hit is not enough.

**Level 2 — Child (small, precise search)**  
- Section split into pieces (e.g. 500–800 tokens each).  
- Each child has `parent_id` → points to its parent row.  
- **Embedded and indexed** — hybrid + rerank run here.

**Ingest example**

```text
Section "2. Leave" (parent, 3,000 tokens)
  ├─ child 1: "Annual leave is 20 days..."
  ├─ child 2: "Sick leave requires..."
  └─ child 3: "Parental leave applies after..."
```

**Chat example**

1. User: “How many sick days?”  
2. Retrieval finds **child 2** (best match).  
3. Backend loads **parent** “2. Leave” (or parent text + child 2).  
4. Prompt gets parent context + highlighted child — **not** the full 200-page PDF.

```text
[Parent section text - truncated if huge]
---
[Matched child excerpt]
```

---

### Is 2-level still “hierarchical”?

**Yes.** Hierarchy = levels of granularity. Two levels is the most common production pattern:

```text
Parent (section)  →  Child (passage)
```

That **is** hierarchical RAG. People say “parent–child” to mean **this specific 2-level design** (small search units, large context units).

---

### 3-level hierarchy (what changes)

```text
Document / Part  →  Section  →  Chunk
     (L0)              (L1)        (L2)
```

Example: textbook → **Part II** → **Chapter 5** → **paragraph chunks**.

| | 2-level (parent–child) | 3-level |
|--|------------------------|---------|
| Levels | Section → passage | Part → section → passage |
| DB | `parent_id` on child | `parent_id` + maybe `grandparent_id` or nested `section_path` |
| Complexity | Low | Medium |
| When needed | Long sections, most enterprise docs | Books, legal codes, multi-part manuals |
| Search | Usually on **bottom** level only | Same — search deepest level, walk up for context |

You can still call level 0 “the document row” without storing it as a chunk — the **file** is the root.

---

### Which is “best”?

**For your app (4+5+6, client docs):**

| Approach | Verdict |
|----------|---------|
| **Heading sections only (no parent–child)** | Best **default** when sections are short enough. |
| **2-level parent–child** | Best **when a section is longer than max chunk** or answers need full-section context. |
| **3-level hierarchy** | **Optional later** — only if you see failures like “need Part + Chapter context, one section chunk isn’t enough.” |

**Parent–child vs “hierarchy 3”** — not competitors:

- Parent–child **=** 2-level hierarchy (section + passages).  
- 3-level **=** parent–child **plus** an extra grouping layer (part/chapter).

**Recommendation**

1. Ship **SECTION + FIXED** (and detect which).  
2. Add **2-level parent–child** inside long sections when tests show snippet-without-context failures.  
3. Skip 3-level until a real doc type proves you need it.

**Bottom line:** Parent–child is hierarchical with **2 levels**; it’s the sweet spot for most RAG. Three levels is for unusually deep documents — not required for “any file type” in v1.

---

**You:** For all three strategies we pick based on docling. How do we know what is parent vs child? Do we need dynamic code — separate functions for parent–child, fixed, heading? What about docling + LLM picks one of three with parameters, not inventing new strategies?

**Us:** **Yes on the code shape. Mostly yes on docling → pick strategy. Parent/child boundaries should be rules, not LLM.**

---

### Architecture you described (correct)

```text
docling parse
  → structure stats (headings, section lengths, page count)
  → pick strategy: SECTION | FIXED | PARENT_CHILD   (+ optional params)
  → run ONE chunker function
  → embed children (and parents only if you choose)
  → optional Layer 2 LLM metadata (separate step)
```

Three **implementations** in code:

- `chunk_fixed(text, chunk_size, overlap)`
- `chunk_by_sections(outline)` — split on every heading level from docling
- `chunk_parent_child(sections, max_child_tokens, overlap)` — calls section split first, then splits **long** sections only

A small **router** (`choose_chunk_strategy(docling_result)`) returns enum + params. No fourth mystery chunker.

---

### Who decides parent vs child? (not the LLM)

**Deterministic rules from docling outline + token limits:**

| Piece | Rule |
|-------|------|
| **Section** | Text from heading A up to (not including) heading B — from docling tree (`2. Policy`, `2.1`, `2.2` each can be a section). |
| **Parent** | That whole section row, **if** section length > `max_chunk_tokens`. |
| **Child** | `chunk_fixed` **inside** that section only (same size/overlap as global fixed). |
| **No parent–child** | Section already short → one chunk per section, `parent_id = null`. |

Example:

```text
2.1 Eligibility (400 tokens)  → 1 chunk, no parent–child
2.2 Limits (3,500 tokens)     → 1 parent "2.2 Limits" + 5 children
```

LLM does **not** label “this sentence is parent.” Code measures length after docling gives sections.

---

### How to pick SECTION vs FIXED vs PARENT_CHILD (router)

**Rules-first (recommended v1)** — from docling only:

```text
if parse failed or no text           → fail ingest
elif heading_count < 2               → FIXED
elif any section > max_chunk_tokens  → PARENT_CHILD (still section-aware)
else                                 → SECTION
```

`PARENT_CHILD` is not a separate document type — it’s **SECTION + split long sections into children**.

So you can even implement as **two chunkers** (`section_aware` and `fixed`) where `section_aware` automatically creates parent/child when needed.

**Optional LLM (closed menu)** — same enum, bounded params:

```json
{
  "strategy": "SECTION" | "FIXED" | "PARENT_CHILD",
  "max_chunk_tokens": 800,
  "overlap": 120
}
```

Input to LLM: **docling summary only** (heading list, counts, max section length, pages) — not full doc.

- If LLM fails or returns garbage → **rules default** (`FIXED` or your rule table).
- LLM does **not** choose parent IDs or chunk boundaries.

**Better than LLM router?** For client safety: **rules first**; add LLM classifier only if rules mis-classify real files in testing. Cheaper, reproducible, easier to debug.

---

### docling + LLM + functions — final recommended flow

```text
1. docling → text + outline + stats
2. router (rules; optional LLM enum) → strategy + params
3. chunker function (pure Python)
4. store chunks (+ parent_id, section_title, heading_level)
5. embed children
6. optional: slim LLM metadata (Module 4) — separate from chunking
```

**Two LLM calls max on ingest** (if you enable both): (A) optional strategy enum, (B) metadata tags. Many teams skip (A) entirely.

---

### Are you right?

| Your idea | Verdict |
|-----------|---------|
| Pick strategy from docling | ✅ Yes |
| Separate functions per approach | ✅ Yes |
| Dynamic parent/child in code | ✅ Yes — driven by **section length**, not user upload type |
| LLM picks only 1 of 3 + params | ✅ OK as optional; rules are safer default |
| LLM decides parent/child boundaries | ❌ No — keep that in code |

**Best combo for product:** **docling + rule router + 2 chunker functions** (section-aware with auto parent–child inside, fixed fallback) + **optional** LLM metadata. Skip LLM strategy picker until you need it.

---

**You:** Rule-based router sounds good. List the rules we’ll use. Also explain “whole section row, if section length > max_chunk_tokens” — the condition and why.

**Us:**

---

### Rule list (v1 — docling → chunk strategy)

**After docling parse, compute these stats (no LLM):**

| Stat | How |
|------|-----|
| `has_text` | Parsed body length > 0 |
| `heading_count` | Number of headings in outline |
| `max_section_tokens` | Longest section (heading → next heading) |
| `avg_section_tokens` | Average section size |
| `mime / extension` | From upload |

**Router rules (order matters — first match wins):**

| # | Rule | Strategy | Why |
|---|------|----------|-----|
| R1 | `not has_text` | **fail ingest** | Nothing to index |
| R2 | `heading_count < 2` | **FIXED** | No real outline (plain notes, wall of text) |
| R3 | `max_section_tokens > max_chunk_tokens` | **SECTION + parent–child inside long sections** | At least one section too big for one chunk |
| R4 | `heading_count >= 2` and all sections ≤ max | **SECTION** (one chunk per section, no parent–child) | Clean handbook-style doc |
| R5 | else | **FIXED** | Safety default |

**Optional tuning rules (later):**

| Rule | Effect |
|------|--------|
| `max_section_tokens > 3 * max_chunk_tokens` | Use smaller child size or more overlap |
| Table-heavy page ratio high | Stay SECTION but flag for UI; or FIXED if parser outline untrusted |
| Single heading covering 90%+ of doc | Treat as **FIXED** (fake outline) |

**Params (env / config, not rules):**

- `max_chunk_tokens` — e.g. 600–800 tokens (your `chunk_size` mapped to tokens)
- `chunk_overlap` — e.g. 100–150 tokens
- `min_headings_for_section` — default `2`

---

### What is a “section row”?

One **section** = one block of text in the docling outline:

```text
Heading: "2.1 Eligibility"
Body:    everything until the next heading ("2.2 Limits")
```

In the DB that becomes one logical unit before you split:

- `section_title`: `"2.1 Eligibility"`
- `heading_level`: `3`
- `content`: full body text for that section  
- (later) `parent_id` / `chunk_level` if you split it

We call that the **section row** — the whole `2.1` piece, not yet broken into children.

---

### The condition: `section length > max_chunk_tokens`

**Meaning**

- Measure **section** size in tokens (or chars proxy).
- Compare to **`max_chunk_tokens`** — the largest chunk you allow in the DB / embedding model context per hit.

**If section is SHORT (≤ max):**

- Store **one chunk** for the whole section.
- No parent–child.
- Example: `2.1` = 400 tokens → 1 chunk.

**If section is LONG (> max):**

- **Parent** = full section text (the whole `2.1` row) — for context at answer time.
- **Children** = split that section with fixed windows + overlap — for search/embed.
- Example: `2.2` = 3,500 tokens, max = 800 → 1 parent + ~5 children.

---

### Why this condition?

| Reason | Explanation |
|--------|-------------|
| **Embedding / retrieval** | Models work best on **small, focused** chunks. One 3,500-token chunk dilutes the vector — wrong paragraph wins search. |
| **Prompt budget** | You only send top-K chunks to the LLM. A huge chunk eats the whole window or gets truncated mid-sentence. |
| **Precision** | User asks about sick leave → you want the **paragraph** that mentions sick leave, not all of “2. Policy”. |
| **Context when needed** | Parent holds full `2.2` so after child 3 hits, the model still sees surrounding policy, not one fragment alone. |

**Why not always parent–child?**

- Extra rows and logic when unnecessary.
- Short `2.1` / `2.2` sections are **already** the right size — one chunk each is simpler and works.

**Why not always split fixed across the whole doc?**

- You lose heading boundaries — “2.1” and “2.2” can end up in the same arbitrary window.
- Section-first keeps citations clean (“§ 2.2 Limits”).

**One line:**  
`length > max_chunk_tokens` means **“this heading’s section is too big to be a single search unit — split for search, keep the full section for context.”**

---

**You:** Show Module 4 clearly — what metadata do we get? Is Layer 1 = Module 5 and Layer 2 = Module 2? I don’t understand the two-layer text.

**Us:** **Layer 2 is Module 4, not Module 2.** Module 2 in this course = chat + RAG (already done). Easy to confuse **Layer 2** with **Module 2**.

---

### Modules vs layers (map)

| Course module | What it is | Metadata role |
|---------------|------------|----------------|
| **Module 5** | Parse PDF/DOCX/HTML/MD (docling) | Produces **Layer 1** as a *side effect* — parser facts, no LLM |
| **Module 4** | LLM structured tags on each doc | Produces **Layer 2** — semantic tags, small schema |
| **Module 2** | Chat + vector RAG | **Not metadata** — already built |
| **Module 6** | Hybrid + rerank | **Not metadata** — better chunk retrieval |

**One ingest pipeline, two metadata layers:**

```text
Upload
  → Module 5: docling (text + outline)     → Layer 1 saved (parser.*)
  → chunk (uses outline from M5)
  → Module 4: one cheap LLM call          → Layer 2 saved (llm.*)  [skip if unchanged]
  → embed + store
```

Layer 1 is **not** “Module 5 instead of Module 4.” You still do **both modules**; Layer 1 is the **free part** that comes from parsing during M5.

---

### Layer 1 — from Module 5 parsing (no LLM, $0 tokens)

**Who writes it:** your Python code reading docling output.

**Where stored:** `documents.metadata.parser` (and/or columns you already have: `filename`, `mime_type`, `byte_size`).

**What you get:**

| Field | Example |
|-------|---------|
| `page_count` | `48` |
| `language` | `en` |
| `headings` | `["2. Policy", "2.1 Eligibility", "2.2 Limits"]` |
| `title_guess` | `Employee Handbook 2024` |
| `parsed_at` | ISO timestamp |
| `chunk_strategy_used` | `SECTION` / `FIXED` (from your router) |

**Used for:** heading-based chunking, Documents UI, debugging — not “what kind of policy is this?” in a smart way.

---

### Layer 2 — Module 4 proper (one LLM call per new/changed file)

**Who writes it:** LLM with Pydantic schema (`gpt-4o-mini` class).

**When:** only **create** or **update** (Module 3 `unchanged` → **skip**, no call).

**Input to LLM (small):** filename + Layer 1 headings/outline + first ~8k chars (not full book).

**Where stored:** `documents.metadata.llm`

**Slim schema (Module 4):**

| Field | Example |
|-------|---------|
| `doc_type` | `policy` |
| `topics` | `["HR", "leave", "termination"]` |
| `summary` | `Staff leave and conduct rules for 2024.` |
| `date_guess` | `2024-01-01` or `null` |
| `entities` | `["ACME Corp"]` (short list) |

**Optional:** `title` only if `title_guess` from Layer 1 is missing or junk.

**If LLM fails:** ingest still succeeds; `metadata.llm` = null.

**Not on every chunk** — only per **document**.

---

### Example `documents.metadata` (both layers)

```json
{
  "parser": {
    "page_count": 48,
    "language": "en",
    "headings": ["2. Policy", "2.1 Eligibility", "2.2 Limits"],
    "title_guess": "Employee Handbook 2024",
    "chunk_strategy": "SECTION",
    "parsed_at": "2026-05-29T12:00:00Z"
  },
  "llm": {
    "doc_type": "policy",
    "topics": ["HR", "leave", "termination"],
    "summary": "Staff leave and conduct rules for 2024.",
    "date_guess": "2024-01-01",
    "entities": ["ACME Corp"]
  }
}
```

`filename`, `mime_type`, `byte_size` stay normal **table columns** — don’t duplicate inside JSON.

---

### Chat time — what runs (cheap)

| Step | Module | Tokens |
|------|--------|--------|
| User asks question | — | — |
| Optional filter docs by `metadata.llm` | 4 | **0** (SQL only) |
| Hybrid + rerank on **chunks** | 6 | rerank API, not full doc |
| Answer with top-K excerpts | 2 chat | mini + small context |

**No** LLM metadata call per message. **No** full document in prompt.

---

### One sentence to remember

**Module 5 gives free parser facts (Layer 1); Module 4 adds one small LLM tag set (Layer 2); Module 6 finds the right chunks; Module 2 chat answers.**

---

**You:** List Module 5 responsibilities from our discussion — docling, chunk, metadata, everything.

**Us:**

---

### Module 5 — full responsibility list (our agreed scope)

Module 5 = **“Get text and structure out of any supported file, chunk it correctly, save Layer 1 metadata.”**  
It does **not** run Layer 2 LLM tags (that’s Module 4).

---

#### 1. File intake & formats

- Accept **PDF, DOCX, HTML, Markdown, TXT** (per PRD).
- Validate MIME/extension and size limits.
- Hand bytes to **docling** (or equivalent parser).

---

#### 2. Parsing (docling)

- Extract **clean text** from each format.
- Build **document outline**: headings at all levels (`2. Policy`, `2.1`, `2.2`, …).
- Collect **parser stats**: page count, language (if detector available), title guess, section lengths.
- **Fail ingest** clearly if no extractable text (don’t index garbage).

---

#### 3. Layer 1 metadata (parser — no LLM)

- Write **`documents.metadata.parser`** (and use existing table columns where they already exist):

  - `page_count`, `language`, `headings`, `title_guess`
  - `chunk_strategy` (which rule path was chosen)
  - `parsed_at`

- **Do not** call LLM here.
- **Do not** duplicate `filename` / `mime_type` / `byte_size` inside JSON if they’re already columns.

---

#### 4. Chunk strategy router (rules from docling stats)

- Compute: `has_text`, `heading_count`, `max_section_tokens`, etc.
- Pick path (first match):

  - no text → fail  
  - &lt; 2 headings → **FIXED**  
  - any section &gt; `max_chunk_tokens` → **SECTION** + parent–child inside long sections  
  - else good outline → **SECTION** (one chunk per short section)  
  - else → **FIXED** fallback  

- Store chosen strategy on parser metadata.

---

#### 5. Chunking (execute in code — three behaviors, two main functions)

- **`chunk_by_sections`**: split on **all** heading levels from outline; if one section too long → **parent** = full section, **children** = fixed windows inside section only.
- **`chunk_fixed`**: size + overlap on full text when no reliable outline.
- Set per chunk row: `content`, `chunk_index`, `section_title`, `heading_level`, `parent_id`, `chunk_level` (`child` / `parent` as needed).
- **Embed and index children** (parents for context at chat time, usually not searched).

---

#### 6. Hand off to rest of ingest (Module 5 ends here)

- Pass chunk texts to **embedding** service (same pipeline as today).
- Insert rows into **`document_chunks`**.
- Set document `status` → `ready` (or `failed`).
- Respect **Module 3**: unchanged file → skip parse/chunk/embed entirely.

---

#### 7. What Module 5 does **not** do

| Not M5 | Owner |
|--------|--------|
| Layer 2 LLM metadata (`doc_type`, `topics`, `summary`) | **Module 4** |
| Hybrid search, rerank | **Module 6** |
| Chat / SSE / citations UI | **Module 2** (done) |
| Content hash / skip unchanged | **Module 3** (done) — M5 **obeys** it |

---

#### 8. Order inside upload pipeline

```text
Module 3 check (unchanged? → stop)
  → Module 5: docling parse
  → Module 5: Layer 1 metadata + router
  → Module 5: chunk + store chunk rows
  → Module 4: Layer 2 LLM metadata (optional call)
  → embed chunks → ready
  → (later chat) Module 6 + Module 2
```

---

#### One-line summary

**Module 5 = parse any supported file → save parser metadata → rule-pick chunking → write chunks → then embedding runs.**

---

**You:** List Module 4 responsibilities like we did for Module 5.

**Us:**

---

### Module 4 — full responsibility list (our agreed scope)

Module 4 = **“One cheap LLM pass per document for semantic tags (Layer 2).”**  
It runs **after** Module 5 parse + chunk. It does **not** parse files or choose chunking.

---

#### 1. When it runs

- **Only** on ingest **create** or **update** (new bytes / changed content).
- **Skip** when Module 3 says `unchanged` — **no LLM call**, keep existing `metadata.llm`.
- Runs **after** Layer 1 (`metadata.parser`) exists from Module 5.

---

#### 2. Input to LLM (small — token control)

- `filename`
- Layer 1: `headings`, `title_guess`, `page_count` (outline summary)
- Text sample: first ~8k chars **or** section intros — **not** full document
- Optional: skip generating `title` if `title_guess` is already good

---

#### 3. Layer 2 metadata (LLM — slim schema)

Write **`documents.metadata.llm`** via Pydantic / structured output (`gpt-4o-mini` class):

| Field | Purpose |
|-------|---------|
| `doc_type` | `policy`, `contract`, `report`, `manual`, `other` |
| `topics` | 3–5 tags, e.g. `["HR", "leave"]` |
| `summary` | 1–2 sentences for UI / filters |
| `date_guess` | best-effort doc date or `null` |
| `entities` | short list of orgs/products (optional) |
| `title` | only if Layer 1 title is missing/junk |

**Not per chunk** — one object per **document** only.

---

#### 4. Fail-open behavior

- LLM error / timeout / invalid JSON → ingest **still succeeds**
- Set `metadata.llm` = `null` (or omit); document → `ready` if chunks/embed OK
- Log error for observability (LangSmith)

---

#### 5. Storage & migration

- Add/use `documents.metadata` jsonb (if not already): namespaces `parser` (M5) + `llm` (M4)
- Optional indexes for filters later, e.g. `metadata->'llm'->>'doc_type'`
- Do **not** duplicate `filename`, `mime_type`, `byte_size` into `llm` blob

---

#### 6. Use at retrieval / UI (optional in v1, design for it)

- **SQL filters** before chunk search: e.g. only `doc_type = policy` (0 tokens at chat)
- **Documents page**: show `summary`, `topics`, `doc_type` badges
- **Chat v1**: can ignore filters and rely on Module 6; add question→filter later

---

#### 7. Config & flags

- `METADATA_EXTRACTION_ENABLED=true/false`
- Same model env as chat (`openai_model`) or dedicated `metadata_model` (mini)
- Document in `.env.example`

---

#### 8. What Module 4 does **not** do

| Not M4 | Owner |
|--------|--------|
| Parse PDF/DOCX, docling, outline | **Module 5** |
| Chunking, parent–child, router rules | **Module 5** |
| Layer 1 parser metadata | **Module 5** |
| Embeddings, `document_chunks` rows | Ingest pipeline (after M5 chunk) |
| Hybrid search, rerank | **Module 6** |
| Chat streaming, citations | **Module 2** (done) |
| Skip unchanged file | **Module 3** (done) — M4 **obeys** it |

---

#### 9. Order in pipeline

```text
Module 5: parse → Layer 1 → chunk rows
  → Module 4: LLM → Layer 2 (llm.*)
  → embed chunks → status ready
```

---

#### One-line summary

**Module 4 = after parse/chunk, one structured LLM call per new/changed doc → save semantic tags → fail open → optional filters/UI.**

---

**You:** Module 6 — short: why use it, what problem, rerank with LLM or reranker model? What does industry use today?

**Us:**

---

### Module 6 — why (problems it fixes)

You have **vector-only** today. It fails when:

- User uses **exact words** (SKU, law cite, person name) but embedding matches vague similar text.
- User **paraphrases** but the doc uses different wording — keyword would help.
- Right chunk is **rank 15** — never reaches your top-K prompt.

**Module 6 fixes retrieval quality**, not ingest. Still **never sends full doc** to chat LLM.

---

### What Module 6 does (2 steps)

**Step 1 — Hybrid search**

- **Vector** (pgvector) = meaning / paraphrase.
- **Keyword** (Postgres full-text / BM25-style) = exact tokens.
- **RRF** merges both ranked lists → ~20–50 **candidates**.

**Step 2 — Rerank**

- Score each `(question, chunk)` with a **reranker model**.
- Keep **top 5–8** for the chat prompt.

```text
question → hybrid (wide net) → rerank (precision) → top-K → Module 2 chat
```

---

### Reranking: LLM or dedicated model?

| Approach | Use? |
|----------|------|
| **Chat LLM** (GPT/Opus scores chunks) | ❌ Expensive, slow, inconsistent — avoid for rerank |
| **Cross-encoder / rerank API** | ✅ **Industry default** |

**Use a reranker model**, not your chat LLM.

**Common choices (2025–2026 production):**

| Option | Type | Notes |
|--------|------|--------|
| **Cohere Rerank** (`rerank-v3.5` / v4) | Managed API | Very common, ~100–300ms, pay per search |
| **Voyage rerank** | Managed API | Similar slot to Cohere |
| **BGE-reranker-v2-m3** | Open-source, self-host | Popular if you want no extra vendor, GPU/CPU |
| **ms-marco MiniLM** | Small OSS cross-encoder | Cheaper/lighter, slightly lower quality |

**Typical pipeline today:** hybrid → **rerank 20–50 down to 5** → **gpt-4o-mini** (or similar) **only for the final answer**.

---

### Industry pattern (2026)

1. Hybrid (BM25/FTS + dense)  
2. RRF fusion  
3. Cross-encoder rerank (Cohere or BGE)  
4. Top 5–10 chunks → generation LLM  

Pure vector-only is treated as **naive** for production. **Reranker before chat** is the biggest single retrieval upgrade.

**For our stack:** Postgres **pgvector + full-text** + RRF in backend; **Cohere Rerank API** or **BGE** (env flag) — not Opus/GPT for reranking.

---

### Module 6 responsibilities (short list)

- Supabase: FTS index on `document_chunks.content` (or RPC for keyword leg).
- Backend: parallel vector + keyword search, RRF merge.
- Backend: reranker call on candidate set; config `RERANK_TOP_N`, `HYBRID_CANDIDATE_K`.
- Wire `RetrievalService` → chat still gets small top-K + sources.
- Env: rerank provider + API key; graceful fallback to hybrid-only if rerank down.

**Does not:** parse, chunk, Layer 1/2 metadata (M5/M4), generate answers (M2).

---

*Add new turns below as we keep discussing.*
