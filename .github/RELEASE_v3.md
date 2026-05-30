## Modules 4, 5 & 6: Robust Retrieval Upgrade

Single delivery — docling parsing, LLM metadata, hybrid search + reranking — on the existing chat flow.

### Module 4: Metadata Extraction

- One `gpt-4o-mini` structured call per new/changed document → `metadata.llm` (fail-open)
- Supabase migration `004_metadata.sql` (`documents.metadata` jsonb + doc_type index)
- `MetadataExtractor` with Pydantic schema during ingest
- Documents UI shows doc_type, topics, and summary

### Module 5: Multi-Format Support

- Docling parsing with pypdf / plain-text fallback (`parsing.py`)
- Structure-aware chunking: FIXED / SECTION / parent–child for long sections
- Upload accepts `.txt`, `.md`, `.pdf`, `.docx`, `.html`
- Supabase migration `005_chunk_structure.sql` (section/parent-child columns, nullable embedding)

### Module 6: Hybrid Search & Reranking

- Vector + full-text search → RRF merge → Cohere rerank → parent context expansion
- Supabase migration `006_hybrid_search.sql` (`content_tsv`, `match_chunks_keyword` RPC)
- `HybridSearchService` and `CohereReranker` (fail-open without `COHERE_API_KEY`)
- Config: `COHERE_API_KEY`, `RERANK_*`, `HYBRID_CANDIDATE_K`

## LangSmith Full RAG Tracing

- `tracing.py` helper with spans for the full pipeline: `chat_turn`, `rag_retrieve`, `hybrid_rrf`, `cohere_rerank`, `build_rag_prompt`, `document_ingest`, `metadata_extract`, `embed_texts`
- Optional `LANGSMITH_LOG_CHUNK_TEXT` for full chunk bodies in traces
- README, `.env.example`, and PROGRESS updated; Modules 4–6 validated E2E

## Setup note

Apply migrations `004_metadata.sql`, `005_chunk_structure.sql`, and `006_hybrid_search.sql` in the Supabase SQL Editor (in order) before testing multi-format upload and hybrid retrieval.

Optional: set `COHERE_API_KEY` for reranking and `LANGSMITH_TRACING=true` for full observability.
