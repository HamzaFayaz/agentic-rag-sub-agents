from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import HTTPException, status

from app.config import settings
from app.services.openai_client import OpenAIClient
from app.services.supabase_client import SupabaseRepository


class ChatService:
    def __init__(self, repo: SupabaseRepository, openai_client: OpenAIClient) -> None:
        self._repo = repo
        self._openai = openai_client

    def _build_messages(
        self, history: list[dict], user_content: str
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": settings.system_prompt},
        ]
        for row in history:
            messages.append({"role": row["role"], "content": row["content"]})
        messages.append({"role": "user", "content": user_content})
        return messages

    async def stream_reply(
        self,
        thread_id: UUID,
        user_id: str,
        content: str,
    ) -> AsyncIterator[str]:
        if not self._repo.verify_thread_owner(thread_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Thread not found or access denied",
            )

        self._repo.insert_message(thread_id, "user", content)
        history = self._repo.list_messages(thread_id)
        # Exclude the message we just inserted from history payload
        history_for_model = history[:-1] if history else []
        messages = self._build_messages(history_for_model, content)

        assistant_parts: list[str] = []
        try:
            async for token in self._openai.stream_chat(messages):
                assistant_parts.append(token)
                yield token
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"OpenAI request failed: {exc}",
            ) from exc

        assistant_content = "".join(assistant_parts)
        if assistant_content:
            self._repo.insert_message(thread_id, "assistant", assistant_content)
