from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.config import settings
from app.services.tracing import build_traced_openai_client


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
