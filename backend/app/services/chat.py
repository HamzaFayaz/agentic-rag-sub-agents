from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.services.openai_client import OpenAIClient
from app.services.retrieval import RetrievalService, RetrievedSource
from app.services.supabase_client import SupabaseRepository
from app.services.tracing import (
    build_traced_rag_system_prompt,
    process_chat_turn_inputs,
    process_chat_turn_outputs,
    traceable_if_enabled,
)


@dataclass
class ChatStreamResult:
    sources: list[RetrievedSource]
    token_iterator: AsyncIterator[str]


class ChatService:
    def __init__(
        self,
        repo: SupabaseRepository,
        openai_client: OpenAIClient,
        retrieval: RetrievalService | None = None,
    ) -> None:
        self._repo = repo
        self._openai = openai_client
        self._retrieval = retrieval or RetrievalService(repo)

    def _build_messages(
        self,
        history: list[dict],
        user_content: str,
        system_content: str,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_content},
        ]
        for row in history:
            if row["role"] == "system":
                continue
            messages.append({"role": row["role"], "content": row["content"]})
        messages.append({"role": "user", "content": user_content})
        return messages

    @traceable_if_enabled(
        name="chat_turn",
        run_type="chain",
        process_inputs=process_chat_turn_inputs,
        process_outputs=process_chat_turn_outputs,
    )
    async def prepare_stream(
        self,
        thread_id: UUID,
        user_id: str,
        content: str,
    ) -> ChatStreamResult:
        if not self._repo.verify_thread_owner(thread_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Thread not found or access denied",
            )

        self._repo.insert_message(thread_id, "user", content)
        history = self._repo.list_messages(thread_id)
        history_for_model = history[:-1] if history else []

        context_blocks, sources = await self._retrieval.retrieve(content)
        system_content = build_traced_rag_system_prompt(context_blocks)
        messages = self._build_messages(history_for_model, content, system_content)

        async def token_stream() -> AsyncIterator[str]:
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
                metadata: dict[str, Any] = {}
                if sources:
                    metadata["sources"] = [s.to_dict() for s in sources]
                self._repo.insert_message(
                    thread_id,
                    "assistant",
                    assistant_content,
                    metadata=metadata,
                )

        return ChatStreamResult(sources=sources, token_iterator=token_stream())
