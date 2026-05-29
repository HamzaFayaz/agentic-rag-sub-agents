import asyncio
from typing import Any

from app.config import settings
from app.services.supabase_client import SupabaseRepository
from app.services.tracing import (
    process_hybrid_rrf_inputs,
    process_hybrid_rrf_outputs,
    traceable_if_enabled,
)


@traceable_if_enabled(
    name="hybrid_rrf",
    run_type="tool",
    process_inputs=process_hybrid_rrf_inputs,
    process_outputs=process_hybrid_rrf_outputs,
)
def reciprocal_rank_fusion(
    vector_hits: list[dict[str, Any]],
    keyword_hits: list[dict[str, Any]],
    k: int = 60,
) -> list[dict[str, Any]]:
    """Merge two ranked lists using Reciprocal Rank Fusion (RRF).

    Each hit must have an "id" key. Returns a merged list sorted by
    descending combined RRF score, with a "combined_score" field added.
    """
    scores: dict[str, float] = {}
    docs_by_id: dict[str, dict[str, Any]] = {}

    for rank, hit in enumerate(vector_hits):
        chunk_id = str(hit["id"])
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
        docs_by_id[chunk_id] = hit

    for rank, hit in enumerate(keyword_hits):
        chunk_id = str(hit["id"])
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
        if chunk_id not in docs_by_id:
            docs_by_id[chunk_id] = hit

    merged = []
    for chunk_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        doc = dict(docs_by_id[chunk_id])
        doc["combined_score"] = score
        merged.append(doc)

    return merged


class HybridSearchService:
    """Runs vector + keyword search in parallel and merges via RRF."""

    def __init__(self, repo: SupabaseRepository) -> None:
        self._repo = repo

    async def search(
        self,
        query: str,
        query_embedding: list[float],
    ) -> list[dict[str, Any]]:
        """Execute hybrid search: parallel vector + keyword, then RRF merge."""
        candidate_k = settings.hybrid_candidate_k
        threshold = settings.rag_match_threshold

        vector_hits, keyword_hits = await asyncio.gather(
            asyncio.to_thread(
                self._repo.match_document_chunks,
                query_embedding,
                match_count=candidate_k,
                match_threshold=threshold,
            ),
            asyncio.to_thread(
                self._repo.match_chunks_keyword,
                query,
                match_count=candidate_k,
            ),
        )

        return reciprocal_rank_fusion(vector_hits, keyword_hits)
