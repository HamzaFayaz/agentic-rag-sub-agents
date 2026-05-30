import logging
from typing import Sequence

import cohere

from app.config import settings
from app.services.tracing import (
    process_cohere_rerank_inputs,
    process_cohere_rerank_outputs,
    traceable_if_enabled,
)

logger = logging.getLogger(__name__)


class CohereReranker:
    """Cohere-based reranker with fail-open semantics.

    If no API key is configured, reranking is disabled, or the API call
    fails, the original document order is preserved (indices 0..n-1).
    """

    def __init__(self) -> None:
        self._client: cohere.AsyncClientV2 | None = None
        if settings.cohere_api_key and settings.rerank_enabled:
            self._client = cohere.AsyncClientV2(api_key=settings.cohere_api_key)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def rerank(
        self, query: str, documents: Sequence[str], top_n: int
    ) -> list[int]:
        result = await self._rerank_traced(query, documents, top_n)
        return result["indices"]

    @traceable_if_enabled(
        name="cohere_rerank",
        run_type="tool",
        process_inputs=process_cohere_rerank_inputs,
        process_outputs=process_cohere_rerank_outputs,
    )
    async def _rerank_traced(
        self, query: str, documents: Sequence[str], top_n: int
    ) -> dict:
        """Return indices and trace-friendly scores."""
        n = min(top_n, len(documents))
        fallback_indices = list(range(n))
        fallback = {
            "indices": fallback_indices,
            "top_indices": fallback_indices,
            "scores": [],
        }

        if not self._client or not documents:
            return fallback

        try:
            response = await self._client.rerank(
                model=settings.rerank_model,
                query=query,
                documents=list(documents),
                top_n=n,
            )
            indices = [r.index for r in response.results]
            scores = [
                {
                    "index": r.index,
                    "relevance_score": getattr(r, "relevance_score", None),
                }
                for r in response.results
            ]
            return {
                "indices": indices,
                "top_indices": indices,
                "scores": scores,
            }
        except Exception:
            logger.warning(
                "Cohere rerank failed; falling back to original order", exc_info=True
            )
            return fallback
