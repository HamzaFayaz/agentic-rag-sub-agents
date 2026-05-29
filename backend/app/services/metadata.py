"""Module 4 – LLM-based metadata extraction for uploaded documents."""

from __future__ import annotations

import logging
from typing import Any, Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config import settings
from app.services.tracing import (
    process_metadata_extract_inputs,
    process_metadata_extract_outputs,
    traceable_if_enabled,
)

logger = logging.getLogger(__name__)

MAX_TEXT_SAMPLE = 8_000


class DocumentMetadata(BaseModel):
    """Structured metadata returned by the LLM."""

    doc_type: Literal["policy", "contract", "report", "manual", "other"] = "other"
    topics: list[str] = Field(default_factory=list, max_length=5)
    summary: str = ""
    date_guess: str | None = None
    entities: list[str] | None = None
    title: str | None = None


_SYSTEM_PROMPT = (
    "You are a document-classification assistant. "
    "Given a filename, parser metadata, and the opening text of a document, "
    "return structured metadata. Be concise: topics ≤ 5, summary ≤ 2 sentences. "
    "If unsure about a field, use the default/null value."
)


def _build_user_message(
    filename: str,
    parser_meta: dict[str, Any],
    text_sample: str,
) -> str:
    meta_lines = "\n".join(f"  {k}: {v}" for k, v in parser_meta.items() if v)
    return (
        f"Filename: {filename}\n"
        f"Parser metadata:\n{meta_lines}\n\n"
        f"--- Document text (first ≤{MAX_TEXT_SAMPLE} chars) ---\n"
        f"{text_sample[:MAX_TEXT_SAMPLE]}"
    )


def build_llm_metadata(meta: DocumentMetadata) -> dict[str, Any]:
    """Wrap a DocumentMetadata into the dict stored under metadata.llm."""
    return meta.model_dump(mode="json")


class MetadataExtractor:
    """Extracts structured metadata from a document via OpenAI structured output."""

    def __init__(self) -> None:
        # Plain client: structured parse responses break LangSmith OpenAI serialization.
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    @traceable_if_enabled(
        name="metadata_extract",
        run_type="llm",
        process_inputs=process_metadata_extract_inputs,
        process_outputs=process_metadata_extract_outputs,
    )
    async def extract(
        self,
        filename: str,
        parser_meta: dict[str, Any],
        text_sample: str,
    ) -> dict[str, Any] | None:
        if not settings.metadata_extraction_enabled:
            return None

        try:
            completion = await self._client.beta.chat.completions.parse(
                model=settings.metadata_model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": _build_user_message(
                            filename, parser_meta, text_sample
                        ),
                    },
                ],
                response_format=DocumentMetadata,
            )
            parsed = completion.choices[0].message.parsed
            if parsed is None:
                return None
            if isinstance(parsed, DocumentMetadata):
                return build_llm_metadata(parsed)
            return build_llm_metadata(DocumentMetadata.model_validate(parsed))
        except Exception:
            logger.exception("Metadata extraction failed for %s – skipping", filename)
            return None
