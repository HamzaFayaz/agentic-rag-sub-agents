from app.config import settings
from app.services.tracing import (
    process_embed_texts_inputs,
    process_embed_texts_outputs,
    traceable_if_enabled,
)


class OpenAIEmbeddingClient:
    def __init__(self) -> None:
        from app.services.tracing import build_traced_openai_client

        self._client = build_traced_openai_client()

    @traceable_if_enabled(
        name="embed_texts",
        run_type="embedding",
        process_inputs=process_embed_texts_inputs,
        process_outputs=process_embed_texts_outputs,
    )
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = await self._client.embeddings.create(
            model=settings.openai_embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]
