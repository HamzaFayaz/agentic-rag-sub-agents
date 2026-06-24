"""Tests for TavilyWebSearchService with mocked httpx."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.web_search import TavilyWebSearchService

TAVILY_RESPONSE = {
    "results": [
        {
            "title": "Python 3.13 Released",
            "url": "https://python.org/downloads/release/python-3130/",
            "content": "Python 3.13 is now available with improved performance.",
        },
        {
            "title": "FastAPI Best Practices",
            "url": "https://fastapi.tiangolo.com/best-practices/",
            "content": "Best practices for building APIs with FastAPI.",
        },
    ]
}


def _fake_settings(**overrides) -> SimpleNamespace:
    """Build a lightweight stand-in for the Pydantic Settings singleton."""
    defaults = dict(
        tavily_api_key=None,
        web_search_enabled=False,
        tavily_search_depth="basic",
        tavily_max_results=5,
    )
    defaults.update(overrides)
    ns = SimpleNamespace(**defaults)
    ns.web_search_active = lambda: bool(ns.web_search_enabled and ns.tavily_api_key)
    return ns


@pytest.fixture()
def _enable_web_search(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.services.web_search.settings",
        _fake_settings(tavily_api_key="tvly-test-key", web_search_enabled=True),
    )


@pytest.fixture()
def _disable_web_search(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.services.web_search.settings",
        _fake_settings(tavily_api_key=None, web_search_enabled=False),
    )


def _mock_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


@pytest.mark.asyncio
@pytest.mark.usefixtures("_enable_web_search")
async def test_search_returns_formatted_results():
    svc = TavilyWebSearchService()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=_mock_response(TAVILY_RESPONSE))

    with patch("app.services.web_search.httpx.AsyncClient", return_value=mock_client):
        results = await svc.search("python 3.13 release")

    assert len(results) == 2
    assert results[0]["title"] == "Python 3.13 Released"
    assert results[0]["url"] == "https://python.org/downloads/release/python-3130/"
    assert "performance" in results[0]["content"]
    assert results[1]["title"] == "FastAPI Best Practices"


@pytest.mark.asyncio
@pytest.mark.usefixtures("_enable_web_search")
async def test_search_sends_correct_payload():
    svc = TavilyWebSearchService()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=_mock_response(TAVILY_RESPONSE))

    with patch("app.services.web_search.httpx.AsyncClient", return_value=mock_client):
        await svc.search("test query")

    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert payload["api_key"] == "tvly-test-key"
    assert payload["query"] == "test query"
    assert payload["search_depth"] == "basic"
    assert payload["max_results"] == 5


@pytest.mark.asyncio
@pytest.mark.usefixtures("_disable_web_search")
async def test_search_disabled_returns_empty():
    svc = TavilyWebSearchService()
    results = await svc.search("anything")
    assert results == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("_enable_web_search")
async def test_search_http_error_returns_empty():
    svc = TavilyWebSearchService()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=_mock_response({}, status_code=500))

    with patch("app.services.web_search.httpx.AsyncClient", return_value=mock_client):
        results = await svc.search("fail query")

    assert results == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("_enable_web_search")
async def test_search_network_error_returns_empty():
    svc = TavilyWebSearchService()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

    with patch("app.services.web_search.httpx.AsyncClient", return_value=mock_client):
        results = await svc.search("network fail")

    assert results == []
