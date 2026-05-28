# RAG theory in this project

This document explains the current Retrieval-Augmented Generation (RAG) design in plain language (no implementation code), based on how this repository works today.

## 1) What type of chunking we use

We use fixed-size character chunking with overlap.

- Text is normalized by collapsing repeated whitespace.
- Text is split into windows of configured size.
- Consecutive windows overlap to preserve boundary context.

Current defaults:

- Chunk size: 600 characters
- Chunk overlap: 120 characters

Supported extraction formats:

- `.txt`, `.md` (UTF-8 decode)
- `.pdf` (extract text from pages)

This is a pragmatic baseline strategy, not semantic/sentence-aware chunking.

## 2) How data is processed (ingestion pipeline)

When a user uploads a document:

1. Validate file type and max size.
2. Create a document record with owner and initial status.
3. Upload original file to Supabase Storage.
4. Mark status as processing.
5. Extract text and split into chunks.
6. Generate embeddings for all chunks.
7. Store chunk text + vectors in Postgres.
8. Mark document as ready (or failed with an error message).

Each upload creates:

- Original file in Storage (raw source)
- Searchable chunk rows in Postgres (retrieval index)

## 3) What vector store we use (pgvector)

Vector storage is Postgres + pgvector inside Supabase.

- `pgvector` adds vector column types to Postgres.
- Each chunk stores one embedding in `vector(1536)`.
- Retrieval uses vector similarity search in SQL.
- HNSW index is used for faster nearest-neighbor queries.

Why 1536 dimensions:

- Matches the configured embedding model `text-embedding-3-small`.

Similarity logic:

- Cosine distance is computed in SQL.
- Similarity is treated as `1 - distance`.
- Results are filtered by a minimum threshold and top-k limit.

## 4) How data is retrieved and passed to the LLM

For each user question:

1. Convert question to an embedding vector.
2. Run vector search RPC over chunk embeddings.
3. Restrict matches to:
   - current user data
   - documents with status ready
   - similarity above threshold
4. Keep top-k matches.
5. Build context blocks from chunk text plus source filename.
6. Build system prompt containing those context blocks.
7. Send to chat model:
   - system prompt (with retrieved context)
   - thread history
   - current user message
8. Stream answer tokens back.

If no chunks are matched, chat still runs but without document grounding context.

## 5) What metadata we currently have

### A) Document metadata

- user id (owner)
- filename
- MIME type
- storage path
- status (`pending`, `processing`, `ready`, `failed`)
- error message
- byte size
- timestamps

### B) Chunk metadata

- document id
- user id
- chunk index
- content text
- embedding vector
- token_count (approximate, word-count style)
- timestamp

### C) Retrieval metadata

Per retrieved hit:

- document id
- filename
- snippet
- similarity score

### D) Message metadata

Assistant message rows can store `sources` metadata so citation chips can be shown in the UI (live and after reload).

## 6) Do we pass metadata to the LLM?

Yes, partially.

Passed to LLM:

- Retrieved chunk text
- Source filename labels

Not passed directly to LLM:

- similarity scores
- document ids
- snippet field
- storage path
- ingestion statuses

Why:

- The model needs text evidence + source identity for grounded answers/citations.
- Operational metadata is mainly for ranking, filtering, logging, and UI.
- Keeping prompts focused reduces noise and token cost.

## 7) What memory type we use right now

Current memory is thread-based persisted chat history with stateless model calls.

- Conversation memory is saved in Supabase (`threads` + `messages`).
- On each new turn, history is reloaded and sent again.
- No provider-managed persistent thread memory is used.
- No separate long-term profile memory layer exists.

So in practice:

- Conversational memory = message history in current thread
- Knowledge memory = indexed document chunks in vector store

## 8) Current limitations (theory perspective)

- Chunking is fixed-window, not semantic chunking.
- Retrieval quality depends on threshold/top-k tuning.
- No reranking stage yet.
- No dedup/incremental indexing strategy yet.
- Metadata injected into prompts is intentionally minimal.

## 9) One-line summary

This system converts uploaded files into overlapped text chunks, embeds them with OpenAI, stores vectors in pgvector, retrieves user-scoped relevant chunks at question time, injects that context into a stateless chat prompt, and stores citation metadata with assistant messages for traceability.

