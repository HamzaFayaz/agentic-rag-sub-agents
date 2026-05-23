from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.services.embedding import OpenAIEmbeddingClient
from app.services.supabase_client import SupabaseRepository


@dataclass
class RetrievedSource:
    document_id: str
    filename: str
    snippet: str
    similarity: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "snippet": self.snippet,
            "similarity": self.similarity,
        }


class RetrievalService:
    def __init__(
        self,
        repo: SupabaseRepository,
        embedding_client: OpenAIEmbeddingClient | None = None,
    ) -> None:
        self._repo = repo
        self._embeddings = embedding_client or OpenAIEmbeddingClient()

    async def retrieve(self, query: str) -> tuple[list[str], list[RetrievedSource]]:
        vectors = await self._embeddings.embed_texts([query])
        if not vectors:
            return [], []

        hits = self._repo.match_document_chunks(
            vectors[0],
            match_count=settings.rag_top_k,
            match_threshold=settings.rag_match_threshold,
        )

        context_blocks: list[str] = []
        sources: list[RetrievedSource] = []
        for hit in hits:
            filename = hit.get("filename") or "document"
            content = hit.get("content") or ""
            similarity = float(hit.get("similarity") or 0)
            document_id = str(hit.get("document_id") or "")

            snippet = content[:200] + ("…" if len(content) > 200 else "")
            sources.append(
                RetrievedSource(
                    document_id=document_id,
                    filename=filename,
                    snippet=snippet,
                    similarity=similarity,
                )
            )
            context_blocks.append(f"[Source: {filename}]\n{content}")

        return context_blocks, sources
