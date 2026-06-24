"""Tests for ToolDispatcher routing and feature-gate logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.tool_dispatcher import KNOWN_TOOLS, ToolDispatcher


def _make_settings(
    *,
    sql_active: bool = False,
    web_active: bool = False,
    sub_agent_active: bool = True,
) -> MagicMock:
    """Return a mock Settings with controllable feature gates."""
    s = MagicMock()
    s.text_to_sql_active.return_value = sql_active
    s.web_search_active.return_value = web_active
    s.sub_agent_active.return_value = sub_agent_active
    return s


def _fake_source() -> MagicMock:
    """A lightweight stand-in for RetrievedSource (avoids cohere import)."""
    src = MagicMock()
    src.to_dict.return_value = {
        "document_id": "doc-1",
        "filename": "test.pdf",
        "snippet": "chunk-1 text",
        "similarity": 0.85,
    }
    return src


def _make_retrieval(
    context_blocks: list[str] | None = None,
    sources: list[MagicMock] | None = None,
) -> MagicMock:
    """Return a mock RetrievalService whose retrieve() returns given data."""
    svc = MagicMock()
    svc.retrieve = AsyncMock(
        return_value=(
            context_blocks or ["chunk-1 text"],
            sources or [_fake_source()],
        )
    )
    return svc


# -- dispatch: search_documents ------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_search_documents():
    """search_documents routes to execute_search_documents and returns results."""
    retrieval = _make_retrieval()
    dispatcher = ToolDispatcher(settings=_make_settings(), retrieval_service=retrieval)

    result = await dispatcher.dispatch("search_documents", {"query": "test query"})

    retrieval.retrieve.assert_awaited_once_with("test query")
    assert result["context_blocks"] == ["chunk-1 text"]
    assert len(result["sources"]) == 1
    assert result["sources"][0]["filename"] == "test.pdf"


# -- dispatch: query_database disabled -----------------------------------------


@pytest.mark.asyncio
async def test_query_database_disabled_no_database_url():
    """query_database raises ValueError when text_to_sql_active() is False."""
    dispatcher = ToolDispatcher(
        settings=_make_settings(sql_active=False),
        retrieval_service=_make_retrieval(),
    )

    with pytest.raises(ValueError, match="query_database is disabled"):
        await dispatcher.dispatch(
            "query_database",
            {"question": "how many docs?", "sql": "SELECT count(*) FROM documents"},
        )


# -- dispatch: web_search disabled ---------------------------------------------


@pytest.mark.asyncio
async def test_web_search_disabled_no_tavily_key():
    """web_search raises ValueError when web_search_active() is False."""
    dispatcher = ToolDispatcher(
        settings=_make_settings(web_active=False),
        retrieval_service=_make_retrieval(),
    )

    with pytest.raises(ValueError, match="web_search is disabled"):
        await dispatcher.dispatch("web_search", {"query": "latest news"})


# -- dispatch: unknown tool ----------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_tool_raises_value_error():
    """An unrecognised tool name raises ValueError immediately."""
    dispatcher = ToolDispatcher(
        settings=_make_settings(),
        retrieval_service=_make_retrieval(),
    )

    with pytest.raises(ValueError, match="Unknown tool: not_a_tool"):
        await dispatcher.dispatch("not_a_tool", {"query": "anything"})


# -- KNOWN_TOOLS constant ------------------------------------------------------


def test_known_tools_constant():
    """KNOWN_TOOLS contains all registered tool names."""
    assert KNOWN_TOOLS == {
        "search_documents",
        "query_database",
        "web_search",
        "analyze_document",
    }


# -- dispatch: analyze_document disabled ---------------------------------------


@pytest.mark.asyncio
async def test_analyze_document_disabled():
    """analyze_document raises ValueError when sub_agent_active() is False."""
    dispatcher = ToolDispatcher(
        settings=_make_settings(sub_agent_active=False),
        retrieval_service=_make_retrieval(),
    )

    with pytest.raises(ValueError, match="analyze_document is disabled"):
        await dispatcher.dispatch(
            "analyze_document",
            {"filename": "doc.pdf", "task": "summarize"},
            user_jwt="jwt",
        )


# -- dispatch: analyze_document enabled ----------------------------------------


@pytest.mark.asyncio
async def test_dispatch_analyze_document_enabled():
    """analyze_document routes to execute_analyze_document when enabled."""
    dispatcher = ToolDispatcher(
        settings=_make_settings(sub_agent_active=True),
        retrieval_service=_make_retrieval(),
    )
    expected = {
        "report": "Summary.",
        "mode": "single_pass",
        "passes": 1,
        "document_id": "doc-1",
        "filename": "handbook.pdf",
    }

    with patch(
        "app.services.tool_dispatcher.execute_analyze_document",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_execute:
        result = await dispatcher.dispatch(
            "analyze_document",
            {"filename": "handbook.pdf", "task": "summarize"},
            user_jwt="user-jwt",
        )

    mock_execute.assert_awaited_once_with(
        filename="handbook.pdf",
        task="summarize",
        user_jwt="user-jwt",
        on_progress=None,
    )
    assert result == expected
