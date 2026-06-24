from typing import Any
from uuid import UUID, uuid4

from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from app.config import settings

DOCUMENTS_BUCKET = "documents"


def _maybe_single_row(result: Any) -> dict[str, Any] | None:
    """Supabase may return None from maybe_single().execute() when no row exists."""
    if result is None:
        return None
    return result.data


class SupabaseRepository:
    def __init__(self, access_token: str) -> None:
        # User JWT must be on both PostgREST and Storage; postgrest.auth() alone
        # leaves Storage on the anon key, which fails storage RLS (403).
        self._client: Client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key,
            options=SyncClientOptions(
                headers={"Authorization": f"Bearer {access_token}"},
            ),
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
        return _maybe_single_row(result) is not None

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
                "id, filename, status, byte_size, content_hash, error_message, "
                "metadata, created_at, updated_at"
            )
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    def get_document_by_filename(
        self, user_id: str, filename: str
    ) -> dict[str, Any] | None:
        result = (
            self._client.table("documents")
            .select("*")
            .eq("user_id", user_id)
            .eq("filename", filename)
            .maybe_single()
            .execute()
        )
        return _maybe_single_row(result)

    def get_document(self, document_id: UUID, user_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table("documents")
            .select("*")
            .eq("id", str(document_id))
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        return _maybe_single_row(result)

    def create_document(
        self,
        user_id: str,
        filename: str,
        mime_type: str,
        storage_path: str,
        byte_size: int,
        status: str = "pending",
        document_id: UUID | None = None,
        content_hash: str | None = None,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "user_id": user_id,
            "filename": filename,
            "mime_type": mime_type,
            "storage_path": storage_path,
            "byte_size": byte_size,
            "status": status,
        }
        if content_hash is not None:
            row["content_hash"] = content_hash
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

    def delete_document_chunks(self, document_id: UUID) -> None:
        self._client.table("document_chunks").delete().eq(
            "document_id", str(document_id)
        ).execute()

    def replace_storage_file(
        self,
        storage_path: str,
        content: bytes,
        mime_type: str,
    ) -> None:
        self.upload_document_file(storage_path, content, mime_type)

    def delete_document(self, document_id: UUID, user_id: str) -> None:
        doc = self.get_document(document_id, user_id)
        if not doc:
            return

        self.delete_document_chunks(document_id)

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

        def _build_row(item: dict[str, Any]) -> dict[str, Any]:
            row: dict[str, Any] = {
                "document_id": str(document_id),
                "user_id": user_id,
                "chunk_index": item["chunk_index"],
                "content": item["content"],
                "embedding": item.get("embedding"),
                "token_count": item.get("token_count"),
                "section_title": item.get("section_title"),
                "heading_level": item.get("heading_level"),
                "chunk_level": item.get("chunk_level"),
            }
            return row

        parents = [c for c in chunks if c.get("chunk_level") == "parent"]
        children = [c for c in chunks if c.get("parent_index") is not None]
        standalone = [
            c
            for c in chunks
            if c.get("chunk_level") != "parent" and c.get("parent_index") is None
        ]

        parent_index_to_id: dict[int, str] = {}

        if parents:
            parent_rows = [_build_row(p) for p in parents]
            result = (
                self._client.table("document_chunks")
                .insert(parent_rows)
                .execute()
            )
            if result.data:
                for parent_chunk, inserted in zip(parents, result.data):
                    parent_index_to_id[parent_chunk["chunk_index"]] = inserted["id"]

        if standalone:
            standalone_rows = [_build_row(s) for s in standalone]
            self._client.table("document_chunks").insert(standalone_rows).execute()

        if children:
            child_rows: list[dict[str, Any]] = []
            for child in children:
                row = _build_row(child)
                parent_idx = child["parent_index"]
                row["parent_id"] = parent_index_to_id.get(parent_idx)
                child_rows.append(row)
            self._client.table("document_chunks").insert(child_rows).execute()

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

    def match_chunks_keyword(
        self,
        query_text: str,
        match_count: int | None = None,
    ) -> list[dict[str, Any]]:
        result = self._client.rpc(
            "match_chunks_keyword",
            {
                "query_text": query_text,
                "match_count": match_count or settings.hybrid_candidate_k,
            },
        ).execute()
        return result.data or []

    def get_chunk_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table("document_chunks")
            .select("id, content, section_title, document_id")
            .eq("id", chunk_id)
            .maybe_single()
            .execute()
        )
        return _maybe_single_row(result)

    def count_ready_documents(self, user_id: str) -> int:
        result = (
            self._client.table("documents")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("status", "ready")
            .execute()
        )
        return result.count or 0

    def list_document_chunks(self, document_id: UUID) -> list[dict[str, Any]]:
        """Return embeddable chunks (parents + standalone), excluding child splits.

        Child chunks duplicate parent section text in smaller pieces; the analyst
        stitches parent/standalone rows ordered by chunk_index for full-document reads.
        """
        result = (
            self._client.table("document_chunks")
            .select("content, chunk_index, token_count, chunk_level")
            .eq("document_id", str(document_id))
            .is_("parent_id", "null")
            .order("chunk_index", desc=False)
            .execute()
        )
        return result.data or []

    def find_documents_by_filename(self, filename: str) -> list[dict[str, Any]]:
        """Case-insensitive filename lookup scoped by RLS to the current user."""
        result = (
            self._client.table("documents")
            .select("id, filename, total_token_count, status")
            .ilike("filename", filename)
            .execute()
        )
        return result.data or []

    def list_ready_filenames(self) -> list[str]:
        """Return ready document filenames for the current user (RLS-scoped)."""
        result = (
            self._client.table("documents")
            .select("filename")
            .eq("status", "ready")
            .order("created_at", desc=True)
            .execute()
        )
        return [str(row["filename"]) for row in (result.data or [])]

    @staticmethod
    def build_storage_path(user_id: str, document_id: UUID, filename: str) -> str:
        safe_name = filename.replace("/", "_").replace("\\", "_")
        return f"{user_id}/{document_id}/{safe_name}"

    @staticmethod
    def new_document_id() -> UUID:
        return uuid4()
