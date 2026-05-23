from typing import Any
from uuid import UUID, uuid4

from supabase import Client, create_client

from app.config import settings

DOCUMENTS_BUCKET = "documents"


class SupabaseRepository:
    def __init__(self, access_token: str) -> None:
        self._client: Client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key,
        )
        self._client.postgrest.auth(access_token)

    def verify_thread_owner(self, thread_id: UUID, user_id: str) -> bool:
        result = (
            self._client.table("threads")
            .select("id")
            .eq("id", str(thread_id))
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        return result.data is not None

    def list_messages(
        self, thread_id: UUID, limit: int | None = None
    ) -> list[dict[str, Any]]:
        cap = limit or settings.max_history_messages
        result = (
            self._client.table("messages")
            .select("role, content, created_at, metadata")
            .eq("thread_id", str(thread_id))
            .order("created_at", desc=False)
            .limit(cap)
            .execute()
        )
        return result.data or []

    def insert_message(
        self,
        thread_id: UUID,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "thread_id": str(thread_id),
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }
        result = self._client.table("messages").insert(payload).execute()
        if not result.data:
            raise RuntimeError("Failed to insert message")
        return result.data[0]

    # --- Documents ---

    def list_documents(self, user_id: str) -> list[dict[str, Any]]:
        result = (
            self._client.table("documents")
            .select(
                "id, filename, status, byte_size, error_message, created_at, updated_at"
            )
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    def get_document(self, document_id: UUID, user_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table("documents")
            .select("*")
            .eq("id", str(document_id))
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        return result.data

    def create_document(
        self,
        user_id: str,
        filename: str,
        mime_type: str,
        storage_path: str,
        byte_size: int,
        status: str = "pending",
        document_id: UUID | None = None,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "user_id": user_id,
            "filename": filename,
            "mime_type": mime_type,
            "storage_path": storage_path,
            "byte_size": byte_size,
            "status": status,
        }
        if document_id is not None:
            row["id"] = str(document_id)
        result = (
            self._client.table("documents")
            .insert(row)
            .execute()
        )
        if not result.data:
            raise RuntimeError("Failed to create document")
        return result.data[0]

    def update_document(
        self,
        document_id: UUID,
        user_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        result = (
            self._client.table("documents")
            .update(updates)
            .eq("id", str(document_id))
            .eq("user_id", user_id)
            .execute()
        )
        if not result.data:
            raise RuntimeError("Failed to update document")
        return result.data[0]

    def delete_document(self, document_id: UUID, user_id: str) -> None:
        doc = self.get_document(document_id, user_id)
        if not doc:
            return

        self._client.table("document_chunks").delete().eq(
            "document_id", str(document_id)
        ).execute()

        self._client.table("documents").delete().eq("id", str(document_id)).execute()

        try:
            self._client.storage.from_(DOCUMENTS_BUCKET).remove([doc["storage_path"]])
        except Exception:
            pass

    def insert_document_chunks(
        self,
        document_id: UUID,
        user_id: str,
        chunks: list[dict[str, Any]],
    ) -> None:
        if not chunks:
            return
        rows = [
            {
                "document_id": str(document_id),
                "user_id": user_id,
                "chunk_index": item["chunk_index"],
                "content": item["content"],
                "embedding": item["embedding"],
                "token_count": item.get("token_count"),
            }
            for item in chunks
        ]
        self._client.table("document_chunks").insert(rows).execute()

    def upload_document_file(
        self,
        storage_path: str,
        content: bytes,
        mime_type: str,
    ) -> None:
        self._client.storage.from_(DOCUMENTS_BUCKET).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": mime_type, "upsert": "true"},
        )

    def match_document_chunks(
        self,
        query_embedding: list[float],
        match_count: int | None = None,
        match_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        result = self._client.rpc(
            "match_document_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": match_count or settings.rag_top_k,
                "match_threshold": match_threshold or settings.rag_match_threshold,
            },
        ).execute()
        return result.data or []

    def count_ready_documents(self, user_id: str) -> int:
        result = (
            self._client.table("documents")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("status", "ready")
            .execute()
        )
        return result.count or 0

    @staticmethod
    def build_storage_path(user_id: str, document_id: UUID, filename: str) -> str:
        safe_name = filename.replace("/", "_").replace("\\", "_")
        return f"{user_id}/{document_id}/{safe_name}"

    @staticmethod
    def new_document_id() -> UUID:
        return uuid4()
