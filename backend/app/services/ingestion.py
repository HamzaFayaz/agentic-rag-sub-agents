from uuid import UUID

from fastapi import HTTPException, status

from app.config import settings
from app.services.chunking import ChunkService
from app.services.embedding import OpenAIEmbeddingClient
from app.services.supabase_client import SupabaseRepository

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}
MIME_BY_EXT = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
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
                detail="Allowed types: .txt, .md, .pdf",
            )

        mime_type = MIME_BY_EXT[ext]
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
        )

        try:
            self._repo.upload_document_file(storage_path, content, mime_type)
            self._repo.update_document(
                document_id, user_id, {"status": "processing"}
            )

            text_chunks = self._chunks.chunk_file(filename, content)
            if not text_chunks:
                raise ValueError("No text content to index")

            embeddings = await self._embeddings.embed_texts(text_chunks)
            chunk_rows = [
                {
                    "chunk_index": index,
                    "content": text,
                    "embedding": vector,
                    "token_count": len(text.split()),
                }
                for index, (text, vector) in enumerate(zip(text_chunks, embeddings))
            ]
            self._repo.insert_document_chunks(document_id, user_id, chunk_rows)

            updated = self._repo.update_document(
                document_id,
                user_id,
                {"status": "ready", "error_message": None},
            )
            return updated
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

    @staticmethod
    def _extension(filename: str) -> str:
        dot = filename.rfind(".")
        if dot == -1:
            return ""
        return filename[dot:].lower()
