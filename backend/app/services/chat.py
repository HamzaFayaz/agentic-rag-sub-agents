from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.config import Settings, settings
from app.services.openai_client import OpenAIClient, parse_tool_calls
from app.services.retrieval import RetrievalService
from app.services.supabase_client import SupabaseRepository
from app.services.tool_contracts import (
    SQL_SCHEMA_HINT,
    ToolEndEvent,
    ToolStartEvent,
    build_available_tools,
)
from app.services.tool_dispatcher import ToolDispatcher
from app.services.tracing import (
    process_chat_turn_inputs,
    process_chat_turn_outputs,
    traceable_if_enabled,
)

logger = logging.getLogger(__name__)

ToolEventCallback = Callable[[ToolStartEvent | ToolEndEvent], Awaitable[None]]

AGENT_SYSTEM_PROMPT = (
    "You are a helpful assistant with access to tools.\n"
    "Choose the right tool for each question:\n"
    "  • Questions about document content, policies, CVs, handbooks → search_documents\n"
    "  • Library stats, counts, file lists, metadata queries → query_database\n"
    "  • External/online information, latest news, 'search online' → web_search\n"
    "If no tool is needed, answer directly.\n"
    "When you use information from search_documents, cite the source filename.\n"
    "If the tools do not return useful information, say so rather than inventing facts.\n\n"
    f"{SQL_SCHEMA_HINT}"
)


@dataclass
class ToolRecord:
    """Attribution entry for a single tool invocation."""
    name: str
    status: str
    sql: str | None = None
    web_urls: list[str] = field(default_factory=list)


@dataclass
class ChatStreamResult:
    sources: list[dict[str, Any]]
    tools: list[ToolRecord]
    token_iterator: AsyncIterator[str]


class ChatService:
    def __init__(
        self,
        repo: SupabaseRepository,
        openai_client: OpenAIClient,
        retrieval: RetrievalService | None = None,
        app_settings: Settings | None = None,
    ) -> None:
        self._repo = repo
        self._openai = openai_client
        self._settings = app_settings or settings
        self._retrieval = retrieval or RetrievalService(repo)
        self._dispatcher = ToolDispatcher(self._settings, self._retrieval)

    def _build_messages(
        self,
        history: list[dict],
        user_content: str,
        system_content: str,
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_content},
        ]
        for row in history:
            if row["role"] == "system":
                continue
            messages.append({"role": row["role"], "content": row["content"]})
        messages.append({"role": "user", "content": user_content})
        return messages

    async def _run_tool_loop(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        user_jwt: str | None,
        on_tool_event: ToolEventCallback | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[ToolRecord]]:
        """Run the agent tool loop up to max iterations.

        Returns ``(sources, tools_used)`` where *sources* are from
        search_documents and *tools_used* tracks every invocation.
        """
        all_sources: list[dict[str, Any]] = []
        tool_records: list[ToolRecord] = []
        max_iter = self._settings.agent_max_tool_iterations

        for _ in range(max_iter):
            completion = await self._openai.create_chat_with_tools(messages, tools)
            parsed = parse_tool_calls(completion)

            if not parsed:
                content = completion.choices[0].message.content
                if content:
                    messages.append({"role": "assistant", "content": content})
                break

            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]),
                        },
                    }
                    for tc in parsed
                ],
            }
            messages.append(assistant_msg)

            for tc in parsed:
                tool_name = tc["name"]
                tool_args = tc["arguments"]

                if on_tool_event:
                    await on_tool_event(ToolStartEvent(tool=tool_name, args=tool_args))

                record = ToolRecord(name=tool_name, status="ok")
                try:
                    result = await self._dispatcher.dispatch(
                        tool_name, tool_args, user_jwt=user_jwt,
                    )
                    tool_content = self._format_tool_result(tool_name, result)

                    if tool_name == "search_documents":
                        all_sources.extend(result.get("sources", []))
                    if tool_name == "query_database":
                        record.sql = result.get("sql")
                    if tool_name == "web_search":
                        record.web_urls = [
                            r["url"] for r in result.get("results", []) if r.get("url")
                        ]

                    if on_tool_event:
                        await on_tool_event(
                            ToolEndEvent(tool=tool_name, status="success", result=result)
                        )
                except Exception as exc:
                    logger.warning("Tool %s failed: %s", tool_name, exc)
                    tool_content = f"Tool error: {exc}"
                    record.status = "error"
                    if on_tool_event:
                        await on_tool_event(
                            ToolEndEvent(
                                tool=tool_name, status="error", result={}, error=str(exc),
                            )
                        )

                tool_records.append(record)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": tool_content,
                })

        return messages, all_sources, tool_records

    @staticmethod
    def _format_tool_result(tool_name: str, result: dict[str, Any]) -> str:
        if tool_name == "search_documents":
            blocks = result.get("context_blocks", [])
            if blocks:
                return "\n\n---\n\n".join(blocks)
            return "No relevant documents found."
        if tool_name == "query_database":
            return result.get("content", json.dumps(result.get("rows", [])))
        if tool_name == "web_search":
            items = result.get("results", [])
            if not items:
                return "No web results found."
            parts = []
            for item in items:
                parts.append(f"[{item.get('title','')}]({item.get('url','')})\n{item.get('content','')}")
            return "\n\n".join(parts)
        return json.dumps(result)

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
        *,
        user_jwt: str | None = None,
        on_tool_event: ToolEventCallback | None = None,
    ) -> ChatStreamResult:
        if not self._repo.verify_thread_owner(thread_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Thread not found or access denied",
            )

        self._repo.insert_message(thread_id, "user", content)
        history = self._repo.list_messages(thread_id)
        history_for_model = history[:-1] if history else []

        messages = self._build_messages(
            history_for_model, content, AGENT_SYSTEM_PROMPT,
        )

        tools = build_available_tools(self._settings)

        messages, all_sources, tool_records = await self._run_tool_loop(
            messages, tools, user_jwt, on_tool_event,
        )

        async def token_stream() -> AsyncIterator[str]:
            assistant_parts: list[str] = []
            try:
                async for token in self._openai.stream_chat_final(messages):
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
                if all_sources:
                    metadata["sources"] = all_sources
                if tool_records:
                    metadata["tools"] = [
                        {
                            "name": t.name,
                            "status": t.status,
                            **({"sql": t.sql} if t.sql else {}),
                            **({"web_urls": t.web_urls} if t.web_urls else {}),
                        }
                        for t in tool_records
                    ]
                self._repo.insert_message(
                    thread_id,
                    "assistant",
                    assistant_content,
                    metadata=metadata,
                )

        return ChatStreamResult(
            sources=all_sources,
            tools=tool_records,
            token_iterator=token_stream(),
        )
