from uuid import UUID

from fastapi import HTTPException, status

from app.config import settings
from app.services.chunking import ChunkService
from app.services.embedding import OpenAIEmbeddingClient
from app.services.hashing import content_hash
from app.services.metadata import MetadataExtractor
from app.services.supabase_client import SupabaseRepository
from app.services.tracing import (
    process_document_ingest_inputs,
    process_document_ingest_outputs,
    traceable_if_enabled,
)

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".html"}
MIME_BY_EXT = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".html": "text/html",
}


class IngestionService:
    def __init__(
        self,
        repo: SupabaseRepository,
        chunk_service: ChunkService | None = None,
        embedding_client: OpenAIEmbeddingClient | None = None,
    ) -> None:
        self._repo = repo
        self._chunks = chunk_service or ChunkService()
        self._embeddings = embedding_client or OpenAIEmbeddingClient()

    async def ingest_upload(
        self,
        user_id: str,
        filename: str,
        content: bytes,
    ) -> dict:
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds {settings.max_upload_bytes} bytes",
            )

        ext = self._extension(filename)
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Allowed types: .txt, .md, .pdf, .docx, .html",
            )

        digest = content_hash(content)
        existing = self._repo.get_document_by_filename(user_id, filename)

        if (
            existing
            and existing.get("status") == "ready"
            and existing.get("content_hash") == digest
        ):
            return {**existing, "ingest_action": "unchanged"}

        mime_type = MIME_BY_EXT[ext]

        if existing:
            return await self._update_existing(
                user_id=user_id,
                existing=existing,
                filename=filename,
                content=content,
                mime_type=mime_type,
                digest=digest,
            )

        return await self._create_new(
            user_id=user_id,
            filename=filename,
            content=content,
            mime_type=mime_type,
            digest=digest,
        )

    async def _create_new(
        self,
        user_id: str,
        filename: str,
        content: bytes,
        mime_type: str,
        digest: str,
    ) -> dict:
        document_id = SupabaseRepository.new_document_id()
        storage_path = SupabaseRepository.build_storage_path(
            user_id, document_id, filename
        )

        doc = self._repo.create_document(
            user_id=user_id,
            filename=filename,
            mime_type=mime_type,
            storage_path=storage_path,
            byte_size=len(content),
            status="pending",
            document_id=document_id,
            content_hash=digest,
        )

        try:
            updated = await self._process_document(
                document_id=document_id,
                user_id=user_id,
                filename=filename,
                content=content,
                mime_type=mime_type,
                storage_path=storage_path,
                digest=digest,
            )
            return {**updated, "ingest_action": "created"}
        except Exception as exc:
            self._repo.update_document(
                document_id,
                user_id,
                {
                    "status": "failed",
                    "error_message": str(exc)[:500],
                },
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    async def _update_existing(
        self,
        user_id: str,
        existing: dict,
        filename: str,
        content: bytes,
        mime_type: str,
        digest: str,
    ) -> dict:
        document_id = UUID(existing["id"])
        storage_path = existing["storage_path"]

        self._repo.delete_document_chunks(document_id)
        self._repo.update_document(
            document_id,
            user_id,
            {
                "status": "processing",
                "byte_size": len(content),
                "content_hash": digest,
                "error_message": None,
            },
        )

        try:
            updated = await self._process_document(
                document_id=document_id,
                user_id=user_id,
                filename=filename,
                content=content,
                mime_type=mime_type,
                storage_path=storage_path,
                digest=digest,
            )
            return {**updated, "ingest_action": "updated"}
        except Exception as exc:
            self._repo.update_document(
                document_id,
                user_id,
                {
                    "status": "failed",
                    "error_message": str(exc)[:500],
                },
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    @traceable_if_enabled(
        name="document_ingest",
        run_type="chain",
        process_inputs=process_document_ingest_inputs,
        process_outputs=process_document_ingest_outputs,
    )
    async def _process_document(
        self,
        document_id: UUID,
        user_id: str,
        filename: str,
        content: bytes,
        mime_type: str,
        storage_path: str,
        digest: str,
    ) -> dict:
        self._repo.replace_storage_file(storage_path, content, mime_type)
        self._repo.update_document(
            document_id, user_id, {"status": "processing", "content_hash": digest}
        )

        chunks, parser_meta = self._chunks.chunk_document(filename, content)
        parser_meta = {**parser_meta, "chunk_count": len(chunks)}

        existing_doc = self._repo.get_document(document_id, user_id) or {}
        existing_metadata = existing_doc.get("metadata") or {}
        merged_metadata = {**existing_metadata, "parser": parser_meta}

        if settings.metadata_extraction_enabled:
            try:
                sample = "".join((c.get("content") or "") for c in chunks)[:8_000]
                llm_meta = await MetadataExtractor().extract(
                    filename=filename,
                    parser_meta=parser_meta,
                    text_sample=sample,
                )
                if llm_meta is not None:
                    merged_metadata["llm"] = llm_meta
            except Exception:
                # Fail-open: indexing must continue even if metadata extraction fails.
                pass

        self._repo.update_document(
            document_id,
            user_id,
            {
                "metadata": merged_metadata,
            },
        )

        embeddable_chunks = [c for c in chunks if c.get("chunk_level") != "parent"]
        embeddings: list[list[float]] = []
        if embeddable_chunks:
            embeddings = await self._embeddings.embed_texts(
                [c.get("content") or "" for c in embeddable_chunks]
            )

        embeddings_by_index = {
            chunk.get("chunk_index"): vector
            for chunk, vector in zip(embeddable_chunks, embeddings)
        }

        chunk_rows = []
        for chunk in chunks:
            chunk_rows.append(
                {
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "embedding": embeddings_by_index.get(chunk["chunk_index"]),
                    "token_count": chunk.get("token_count"),
                    "section_title": chunk.get("section_title"),
                    "heading_level": chunk.get("heading_level"),
                    "parent_index": chunk.get("parent_index"),
                    "chunk_level": chunk.get("chunk_level"),
                }
            )

        self._repo.insert_document_chunks(document_id, user_id, chunk_rows)

        return self._repo.update_document(
            document_id,
            user_id,
            {
                "status": "ready",
                "content_hash": digest,
                "error_message": None,
            },
        )

    @staticmethod
    def _extension(filename: str) -> str:
        dot = filename.rfind(".")
        if dot == -1:
            return ""
        return filename[dot:].lower()
