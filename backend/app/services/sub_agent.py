"""Document analyst sub-agent — isolated context, token-aware single/multi pass."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.services.parsing import estimate_tokens
from app.services.supabase_client import SupabaseRepository
from app.services.tracing import (
    process_document_analyze_inputs,
    process_document_analyze_outputs,
    traceable_if_enabled,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], None]


class AnalystReport(BaseModel):
    report: str
    mode: Literal["single_pass", "multi_pass"]
    passes: int
    document_id: str
    filename: str


def fits_budget(total_tokens: int, settings: Settings | None = None) -> bool:
    budget = (settings or get_settings()).sub_agent_context_token_budget
    return total_tokens <= budget


def batch_chunks(
    chunks: list[dict[str, Any]],
    batch_token_budget: int,
) -> list[list[dict[str, Any]]]:
    """Split chunks into batches that fit within batch_token_budget."""
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_tokens = 0

    for chunk in chunks:
        tokens = chunk.get("token_count") or estimate_tokens(
            str(chunk.get("content") or "")
        )
        if current and current_tokens + tokens > batch_token_budget:
            batches.append(current)
            current = []
            current_tokens = 0
        current.append(chunk)
        current_tokens += tokens

    if current:
        batches.append(current)

    return batches


def _chunk_tokens(chunk: dict[str, Any]) -> int:
    return chunk.get("token_count") or estimate_tokens(
        str(chunk.get("content") or "")
    )


def _stitch_chunks(chunks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for chunk in chunks:
        content = str(chunk.get("content") or "").strip()
        if content:
            parts.append(content)
    return "\n\n".join(parts)


class DocumentAnalystService:
    """Isolated document analyst — no main-agent tools, compact report output."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @traceable_if_enabled(
        name="document_analyze",
        run_type="chain",
        process_inputs=process_document_analyze_inputs,
        process_outputs=process_document_analyze_outputs,
    )
    async def analyze(
        self,
        document_id: UUID,
        filename: str,
        task: str,
        user_jwt: str,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> AnalystReport:
        repo = SupabaseRepository(user_jwt)
        chunks = repo.list_document_chunks(document_id)
        if not chunks:
            raise ValueError(f"No readable chunks found for {filename}")

        total_tokens = sum(_chunk_tokens(c) for c in chunks)
        if fits_budget(total_tokens, self._settings):
            report, passes = await self._single_pass(
                chunks, filename, task, on_progress=on_progress
            )
            mode: Literal["single_pass", "multi_pass"] = "single_pass"
        else:
            report, passes = await self._multi_pass(
                chunks, filename, task, on_progress=on_progress
            )
            mode = "multi_pass"

        return AnalystReport(
            report=report,
            mode=mode,
            passes=passes,
            document_id=str(document_id),
            filename=filename,
        )

    async def _single_pass(
        self,
        chunks: list[dict[str, Any]],
        filename: str,
        task: str,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> tuple[str, int]:
        if on_progress:
            on_progress(1, 1, "single_pass")
        text = _stitch_chunks(chunks)
        report = await self._call_analyst_llm(
            system=(
                f"You are a document analyst reading '{filename}'. "
                "Produce a compact, structured report for the main assistant. "
                "Do not repeat the full document — summarize key findings only."
            ),
            user=f"Task: {task}\n\nDocument:\n{text}",
            pass_label="single_pass",
        )
        return report, 1

    async def _multi_pass(
        self,
        chunks: list[dict[str, Any]],
        filename: str,
        task: str,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> tuple[str, int]:
        budget = self._settings.sub_agent_context_token_budget
        batches = batch_chunks(chunks, budget)
        max_passes = self._settings.sub_agent_internal_max_passes
        if len(batches) > max_passes - 1:
            batches = batches[: max_passes - 1]
            logger.warning(
                "Document %s exceeds pass cap; truncating to %d map batches",
                filename,
                len(batches),
            )

        total_passes = len(batches) + 1
        running_notes = ""

        for i, batch in enumerate(batches, start=1):
            if on_progress:
                on_progress(i, total_passes, "multi_pass")
            batch_text = _stitch_chunks(batch)
            running_notes = await self._call_analyst_llm(
                system=(
                    f"You are analyzing '{filename}' in sections. "
                    "Update running notes with key points from this section. "
                    "Keep notes concise — they feed a final report."
                ),
                user=(
                    f"Task: {task}\n\n"
                    f"Section {i} of {len(batches)}:\n{batch_text}\n\n"
                    f"Previous notes:\n{running_notes or '(none)'}"
                ),
                pass_label=f"multi_pass_map_{i}",
            )

        if on_progress:
            on_progress(total_passes, total_passes, "multi_pass")

        report = await self._call_analyst_llm(
            system=(
                f"You are a document analyst for '{filename}'. "
                "Synthesize running notes into a compact final report for the "
                "main assistant. Do not dump the full document."
            ),
            user=f"Task: {task}\n\nRunning notes:\n{running_notes}",
            pass_label="multi_pass_reduce",
        )
        return report, total_passes

    @traceable_if_enabled(name="document_analyze_pass", run_type="llm")
    async def _call_analyst_llm(
        self,
        system: str,
        user: str,
        *,
        pass_label: str,
    ) -> str:
        from app.services.tracing import build_traced_openai_client

        client = build_traced_openai_client()
        response = await client.chat.completions.create(
            model=self._settings.sub_agent_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=self._settings.sub_agent_output_max_tokens,
        )
        return (response.choices[0].message.content or "").strip()
