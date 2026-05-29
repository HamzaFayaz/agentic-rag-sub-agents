from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.services.embedding import OpenAIEmbeddingClient
from app.services.hybrid import HybridSearchService
from app.services.reranker import CohereReranker
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
        query_vectors = await self._embeddings.embed_texts([query])
        if not query_vectors:
            return [], []

        candidates = await HybridSearchService(self._repo).search(
            query=query,
            query_embedding=query_vectors[0],
        )
        if not candidates:
            return [], []

        reranker = CohereReranker()
        candidate_contents = [str(c.get("content") or "") for c in candidates]
        reranked_indices = await reranker.rerank(
            query=query,
            documents=candidate_contents,
            top_n=settings.rerank_top_n,
        )

        selected_hits = [candidates[i] for i in reranked_indices if 0 <= i < len(candidates)]
        hits = selected_hits[: settings.rag_top_k]

        context_blocks: list[str] = []
        sources: list[RetrievedSource] = []
        for hit in hits:
            filename = hit.get("filename") or "document"
            content = hit.get("content") or ""
            score = float(hit.get("combined_score") or hit.get("similarity") or 0)
            document_id = str(hit.get("document_id") or "")
            parent_id = hit.get("parent_id")

            snippet = content[:200] + ("…" if len(content) > 200 else "")
            sources.append(
                RetrievedSource(
                    document_id=document_id,
                    filename=filename,
                    snippet=snippet,
                    similarity=score,
                )
            )

            if parent_id:
                parent = self._repo.get_chunk_by_id(str(parent_id))
                parent_content = str((parent or {}).get("content") or "")
                parent_title = str((parent or {}).get("section_title") or "Untitled section")
                if parent_content:
                    context_blocks.append(
                        "\n".join(
                            [
                                f"[Source: {filename}]",
                                f"[Section: {parent_title}]",
                                "Parent section:",
                                parent_content,
                                "",
                                "Matched excerpt:",
                                content,
                            ]
                        )
                    )
                    continue

            context_blocks.append(f"[Source: {filename}]\n{content}")

        return context_blocks, sources
