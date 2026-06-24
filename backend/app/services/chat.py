import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException, status

from app.config import get_settings
from app.services.openai_client import OpenAIClient, parse_tool_calls
from app.services.retrieval import RetrievalService, RetrievedSource
from app.services.supabase_client import SupabaseRepository
from app.services.tool_contracts import build_available_tools
from app.services.tool_dispatcher import ToolDispatcher
from app.services.tracing import (
    process_chat_turn_inputs,
    process_chat_turn_outputs,
    traceable_if_enabled,
)

_AGENT_ROUTING_PROMPT = (
    "You have tools to answer questions about the user's document library.\n"
    "- search_documents: use for questions about document prose or content "
    "(policies, CV skills, handbook sections) when you need targeted excerpts "
    "or pinpoint facts.\n"
    "- analyze_document: use for whole-document summaries, deep reads, or "
    "comparing specific files by filename. NOT for pinpoint facts — use "
    "search_documents for targeted excerpts.\n"
    "- query_database: use for counts, lists, filters, and aggregates over "
    "library metadata (how many documents, largest file, documents by type).\n"
    "- web_search: use when the user asks for online, current, or external "
    "information (e.g. latest news, search the web).\n"
    "Pick the right tool before answering. For pinpoint facts in document "
    "text, use search_documents. For whole-document analysis or compare tasks, "
    "use analyze_document. For library statistics, use query_database. For "
    "explicit web or current-events requests, use web_search directly without "
    "RAG or SQL."
)


@dataclass
class ChatStreamEvent:
    event: Literal["tool_start", "tool_end", "sources", "token", "subagent_progress"]
    data: dict[str, Any]


@dataclass
class ChatTurnState:
    sources: list[RetrievedSource] = field(default_factory=list)
    tools_meta: list[dict[str, Any]] = field(default_factory=list)


def _assistant_message_dict(message: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": "assistant",
        "content": message.content or None,
    }
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in message.tool_calls
        ]
    return payload


def _format_tool_result(tool_name: str, result: dict[str, Any]) -> str:
    if tool_name == "search_documents":
        blocks = result.get("context_blocks") or []
        if not blocks:
            return "No relevant documents found."
        return "\n\n---\n\n".join(blocks)

    if tool_name == "query_database":
        if result.get("error"):
            return str(result["error"])
        return str(result.get("content") or "No rows returned.")

    if tool_name == "web_search":
        lines: list[str] = []
        for item in result.get("results") or []:
            title = item.get("title") or "Untitled"
            url = item.get("url") or ""
            snippet = item.get("content") or ""
            lines.append(f"- [{title}]({url}): {snippet}")
        return "\n".join(lines) if lines else "No web results found."

    if tool_name == "analyze_document":
        if result.get("error"):
            return str(result["error"])
        return str(result.get("report") or "")

    return str(result)


def _tool_meta_from_result(
    tool_name: str,
    status: Literal["ok", "error"],
    result: dict[str, Any],
) -> dict[str, Any]:
    meta: dict[str, Any] = {"name": tool_name, "status": status}
    if tool_name == "query_database":
        meta["sql"] = result.get("sql")
    if tool_name == "web_search":
        meta["web_urls"] = [
            item.get("url", "")
            for item in result.get("results") or []
            if item.get("url")
        ]
    if tool_name == "analyze_document":
        meta["mode"] = result.get("mode")
        meta["passes"] = result.get("passes")
        meta["document_id"] = result.get("document_id")
        meta["filename"] = result.get("filename")
    return meta


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
        self._settings = get_settings()
        self._dispatcher = ToolDispatcher(self._settings, self._retrieval)

    def _build_system_content(self) -> str:
        return f"{self._settings.system_prompt}\n\n{_AGENT_ROUTING_PROMPT}"

    def _build_messages(
        self,
        history: list[dict],
        user_content: str,
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._build_system_content()},
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
    async def stream_turn(
        self,
        thread_id: UUID,
        user_id: str,
        content: str,
        user_jwt: str,
    ) -> AsyncIterator[ChatStreamEvent]:
        if not self._repo.verify_thread_owner(thread_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Thread not found or access denied",
            )

        self._repo.insert_message(thread_id, "user", content)
        history = self._repo.list_messages(thread_id)
        history_for_model = history[:-1] if history else []

        messages = self._build_messages(history_for_model, content)
        tools = build_available_tools(self._settings)
        state = ChatTurnState()
        assistant_parts: list[str] = []
        analyze_document_count = 0

        try:
            answered = False
            for _ in range(self._settings.agent_max_tool_iterations):
                completion = await self._openai.create_chat_with_tools(
                    messages, tools
                )
                assistant_message = completion.choices[0].message
                tool_calls = parse_tool_calls(assistant_message.tool_calls)

                if not tool_calls:
                    async for token in self._openai.stream_chat_final(messages):
                        assistant_parts.append(token)
                        yield ChatStreamEvent(
                            event="token",
                            data={"content": token},
                        )
                    answered = True
                    break

                messages.append(_assistant_message_dict(assistant_message))

                for call in tool_calls:
                    yield ChatStreamEvent(
                        event="tool_start",
                        data={"tool": call.name, "args": call.arguments},
                    )

                    if (
                        call.name == "analyze_document"
                        and analyze_document_count
                        >= self._settings.sub_agent_max_per_turn
                    ):
                        max_analyses = self._settings.sub_agent_max_per_turn
                        result = {
                            "error": (
                                f"Maximum {max_analyses} document analyses per "
                                "turn — pick the two most relevant documents"
                            ),
                        }
                        tool_status: Literal["ok", "error"] = "error"
                    else:
                        if call.name == "analyze_document":
                            analyze_document_count += 1

                        progress_queue: asyncio.Queue[dict[str, Any]] | None = (
                            asyncio.Queue()
                            if call.name == "analyze_document"
                            else None
                        )

                        def on_subagent_progress(
                            pass_num: int,
                            total_passes: int,
                            mode: str,
                            *,
                            _queue: asyncio.Queue[dict[str, Any]] | None = (
                                progress_queue
                            ),
                            _filename: str = str(
                                call.arguments.get("filename", "")
                            ),
                        ) -> None:
                            if _queue is not None:
                                _queue.put_nowait(
                                    {
                                        "pass": pass_num,
                                        "total_passes": total_passes,
                                        "mode": mode,
                                        "filename": _filename,
                                    }
                                )

                        try:
                            dispatch_task = asyncio.create_task(
                                self._dispatcher.dispatch(
                                    call.name,
                                    call.arguments,
                                    user_jwt=user_jwt,
                                    on_subagent_progress=(
                                        on_subagent_progress
                                        if call.name == "analyze_document"
                                        else None
                                    ),
                                )
                            )

                            while not dispatch_task.done():
                                if progress_queue is not None:
                                    while True:
                                        try:
                                            progress_data = (
                                                progress_queue.get_nowait()
                                            )
                                        except asyncio.QueueEmpty:
                                            break
                                        yield ChatStreamEvent(
                                            event="subagent_progress",
                                            data=progress_data,
                                        )
                                await asyncio.sleep(0)

                            if progress_queue is not None:
                                while not progress_queue.empty():
                                    yield ChatStreamEvent(
                                        event="subagent_progress",
                                        data=progress_queue.get_nowait(),
                                    )

                            result = dispatch_task.result()
                            tool_status = (
                                "error" if result.get("error") else "ok"
                            )
                        except ValueError as exc:
                            result = {"error": str(exc)}
                            tool_status = "error"

                    if call.name == "search_documents":
                        raw_sources = result.get("sources") or []
                        for item in raw_sources:
                            state.sources.append(
                                RetrievedSource(
                                    document_id=str(item.get("document_id", "")),
                                    filename=str(item.get("filename", "")),
                                    snippet=str(item.get("snippet", "")),
                                    similarity=float(item.get("similarity", 0.0)),
                                )
                            )
                        if state.sources:
                            yield ChatStreamEvent(
                                event="sources",
                                data={
                                    "sources": [
                                        s.to_dict() for s in state.sources
                                    ]
                                },
                            )

                    state.tools_meta.append(
                        _tool_meta_from_result(call.name, tool_status, result)
                    )

                    yield ChatStreamEvent(
                        event="tool_end",
                        data={
                            "tool": call.name,
                            "status": tool_status,
                            "result": result,
                            "error": result.get("error"),
                        },
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": _format_tool_result(call.name, result),
                        }
                    )

            if not answered:
                async for token in self._openai.stream_chat_final(messages):
                    assistant_parts.append(token)
                    yield ChatStreamEvent(
                        event="token",
                        data={"content": token},
                    )

        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"OpenAI request failed: {exc}",
            ) from exc

        assistant_content = "".join(assistant_parts)
        if assistant_content:
            metadata: dict[str, Any] = {}
            if state.sources:
                metadata["sources"] = [s.to_dict() for s in state.sources]
            if state.tools_meta:
                metadata["tools"] = state.tools_meta
            self._repo.insert_message(
                thread_id,
                "assistant",
                assistant_content,
                metadata=metadata,
            )
