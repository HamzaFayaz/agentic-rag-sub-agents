import logging
from typing import Sequence

import cohere

from app.config import settings

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
        """Return indices of the top_n most relevant documents.

        Fail-open: returns original order sliced to top_n on any error.
        """
        n = min(top_n, len(documents))
        fallback = list(range(n))

        if not self._client or not documents:
            return fallback

        try:
            response = await self._client.rerank(
                model=settings.rerank_model,
                query=query,
                documents=list(documents),
                top_n=n,
            )
            return [r.index for r in response.results]
        except Exception:
            logger.warning("Cohere rerank failed; falling back to original order", exc_info=True)
            return fallback
