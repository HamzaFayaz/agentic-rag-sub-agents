import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageToolCall

from app.config import settings
from app.services.tracing import build_traced_openai_client


def _build_client() -> AsyncOpenAI:
    return build_traced_openai_client()


@dataclass(frozen=True)
class ParsedToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


def parse_tool_calls(
    tool_calls: list[ChatCompletionMessageToolCall] | None,
) -> list[ParsedToolCall]:
    if not tool_calls:
        return []

    parsed: list[ParsedToolCall] = []
    for call in tool_calls:
        raw_args = call.function.arguments or "{}"
        try:
            arguments = json.loads(raw_args)
        except json.JSONDecodeError:
            arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        parsed.append(
            ParsedToolCall(
                id=call.id,
                name=call.function.name,
                arguments=arguments,
            )
        )
    return parsed


class OpenAIClient:
    def __init__(self) -> None:
        self._client = _build_client()

    async def stream_chat(
        self, messages: list[dict[str, Any]]
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
    ) -> Any:
        return await self._client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

    async def stream_chat_final(
        self, messages: list[dict[str, Any]]
    ) -> AsyncIterator[str]:
        async for token in self.stream_chat(messages):
            yield token
