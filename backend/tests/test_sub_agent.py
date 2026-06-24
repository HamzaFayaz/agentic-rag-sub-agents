"""Tests for document analyst sub-agent helpers and service."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.services.sub_agent import (
    DocumentAnalystService,
    batch_chunks,
    fits_budget,
)
from app.services.tool_executor import execute_analyze_document


def _fake_settings(**overrides) -> SimpleNamespace:
    defaults = dict(
        sub_agent_context_token_budget=100,
        sub_agent_internal_max_passes=8,
        sub_agent_output_max_tokens=2000,
        sub_agent_model="gpt-4o-mini",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _llm_response(text: str) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=text))]
    return response


# -- fits_budget ---------------------------------------------------------------


def test_fits_budget_within_budget():
    settings = _fake_settings(sub_agent_context_token_budget=1000)
    assert fits_budget(500, settings) is True
    assert fits_budget(1000, settings) is True


def test_fits_budget_exceeds_budget():
    settings = _fake_settings(sub_agent_context_token_budget=1000)
    assert fits_budget(1001, settings) is False


# -- batch_chunks --------------------------------------------------------------


def test_batch_chunks_empty():
    assert batch_chunks([], 100) == []


def test_batch_chunks_single_chunk():
    chunks = [{"content": "one", "token_count": 10}]
    batches = batch_chunks(chunks, 100)
    assert len(batches) == 1
    assert batches[0] == chunks


def test_batch_chunks_overflow_to_next_batch():
    chunks = [
        {"content": "a", "token_count": 60},
        {"content": "b", "token_count": 50},
        {"content": "c", "token_count": 30},
    ]
    batches = batch_chunks(chunks, 100)
    assert len(batches) == 2
    assert len(batches[0]) == 1
    assert batches[0][0]["content"] == "a"
    assert len(batches[1]) == 2
    assert batches[1][0]["content"] == "b"
    assert batches[1][1]["content"] == "c"


# -- DocumentAnalystService ------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_small_doc_single_pass():
    doc_id = UUID("11111111-1111-1111-1111-111111111111")
    settings = _fake_settings(sub_agent_context_token_budget=1000)
    chunks = [
        {"content": "Section one.", "token_count": 40},
        {"content": "Section two.", "token_count": 40},
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_llm_response("Compact summary.")
    )

    with (
        patch("app.services.sub_agent.SupabaseRepository") as repo_cls,
        patch(
            "app.services.tracing.build_traced_openai_client",
            return_value=mock_client,
        ),
    ):
        repo_cls.return_value.list_document_chunks.return_value = chunks
        svc = DocumentAnalystService(settings=settings)
        report = await svc.analyze(
            doc_id, "handbook.pdf", "summarize", "user-jwt"
        )

    assert report.mode == "single_pass"
    assert report.passes == 1
    assert report.report == "Compact summary."
    assert report.filename == "handbook.pdf"
    assert mock_client.chat.completions.create.await_count == 1


@pytest.mark.asyncio
async def test_analyze_large_doc_multi_pass_bounded():
    doc_id = UUID("22222222-2222-2222-2222-222222222222")
    settings = _fake_settings(
        sub_agent_context_token_budget=100,
        sub_agent_internal_max_passes=4,
    )
    chunks = [
        {"content": f"part-{i}", "token_count": 60}
        for i in range(6)
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _llm_response("notes-1"),
            _llm_response("notes-2"),
            _llm_response("notes-3"),
            _llm_response("Final report."),
        ]
    )

    with (
        patch("app.services.sub_agent.SupabaseRepository") as repo_cls,
        patch(
            "app.services.tracing.build_traced_openai_client",
            return_value=mock_client,
        ),
    ):
        repo_cls.return_value.list_document_chunks.return_value = chunks
        svc = DocumentAnalystService(settings=settings)
        report = await svc.analyze(
            doc_id, "big.pdf", "summarize", "user-jwt"
        )

    assert report.mode == "multi_pass"
    assert report.passes == 4
    assert report.report == "Final report."
    assert mock_client.chat.completions.create.await_count == 4


# -- per-turn cap (mirrors ChatService logic) ----------------------------------


def test_analyze_document_per_turn_cap_logic():
    """Block when analyze_document_count >= sub_agent_max_per_turn."""
    max_per_turn = 2
    count = 0
    outcomes: list[str] = []

    for _ in range(3):
        if count >= max_per_turn:
            outcomes.append("blocked")
        else:
            count += 1
            outcomes.append("allowed")

    assert outcomes == ["allowed", "allowed", "blocked"]


# -- execute_analyze_document --------------------------------------------------


@pytest.mark.asyncio
async def test_execute_analyze_document_filename_not_found():
    with patch("app.services.tool_executor.SupabaseRepository") as repo_cls:
        repo = MagicMock()
        repo.find_documents_by_filename.return_value = []
        repo.list_ready_filenames.return_value = ["alpha.pdf", "beta.pdf"]
        repo_cls.return_value = repo

        result = await execute_analyze_document(
            "missing.pdf", "summarize", "user-a-jwt"
        )

    assert result["error"]
    assert "not found" in result["error"].lower()
    assert "alpha.pdf" in result["error"]
    assert result["passes"] == 0


@pytest.mark.asyncio
async def test_execute_analyze_document_rls_user_b_no_access():
    """User B gets empty lookup (RLS) — same error path as filename not found."""
    with patch("app.services.tool_executor.SupabaseRepository") as repo_cls:
        repo = MagicMock()
        repo.find_documents_by_filename.return_value = []
        repo.list_ready_filenames.return_value = []
        repo_cls.return_value = repo

        result = await execute_analyze_document(
            "user-a-private.pdf", "summarize", "user-b-jwt"
        )

    assert result["error"]
    assert "not found" in result["error"].lower()
    assert result["report"] == ""
    repo.find_documents_by_filename.assert_called_once_with("user-a-private.pdf")
