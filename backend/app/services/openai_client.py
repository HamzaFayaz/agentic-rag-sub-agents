import os
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.config import settings


def _build_client() -> AsyncOpenAI:
    if settings.langsmith_tracing and settings.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
        os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
        os.environ.setdefault("LANGSMITH_TRACING", "true")

        from langsmith.wrappers import wrap_openai

        return wrap_openai(
            AsyncOpenAI(api_key=settings.openai_api_key),
        )

    return AsyncOpenAI(api_key=settings.openai_api_key)


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
