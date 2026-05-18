from typing import Any
from uuid import UUID

from supabase import Client, create_client

from app.config import settings


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
            .select("role, content, created_at")
            .eq("thread_id", str(thread_id))
            .order("created_at", desc=False)
            .limit(cap)
            .execute()
        )
        return result.data or []

    def insert_message(
        self, thread_id: UUID, role: str, content: str
    ) -> dict[str, Any]:
        result = (
            self._client.table("messages")
            .insert(
                {
                    "thread_id": str(thread_id),
                    "role": role,
                    "content": content,
                }
            )
            .execute()
        )
        if not result.data:
            raise RuntimeError("Failed to insert message")
        return result.data[0]
