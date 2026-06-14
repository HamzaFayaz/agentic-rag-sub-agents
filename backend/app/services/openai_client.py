from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from app.config import settings
from app.services.tracing import build_traced_openai_client

logger = logging.getLogger(__name__)


def _build_client() -> AsyncOpenAI:
    return build_traced_openai_client()


class OpenAIClient:
    def __init__(self) -> None:
        self._client = _build_client()

    async def stream_chat(
        self, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def create_chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ChatCompletion:
        """Non-streaming completion that may include tool_calls."""
        return await self._client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=tools,
        )

    async def stream_chat_final(
        self, messages: list[dict[str, Any]]
    ) -> AsyncIterator[str]:
        """Stream the final answer after the tool loop completes."""
        stream = await self._client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


def parse_tool_calls(
    completion: ChatCompletion,
) -> list[dict[str, Any]]:
    """Extract tool calls from a chat completion response.

    Returns a list of dicts: ``[{"id": ..., "name": ..., "arguments": {...}}, ...]``
    """
    choice = completion.choices[0]
    if choice.finish_reason != "tool_calls" or not choice.message.tool_calls:
        return []

    parsed: list[dict[str, Any]] = []
    for tc in choice.message.tool_calls:
        try:
            args = json.loads(tc.function.arguments)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse arguments for tool %s", tc.function.name)
            args = {}
        parsed.append({"id": tc.id, "name": tc.function.name, "arguments": args})
    return parsed
