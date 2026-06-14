"""Tavily web search service — fail-open when key is missing or disabled."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.services.tracing import (
    process_web_search_inputs,
    process_web_search_outputs,
    traceable_if_enabled,
)

logger = logging.getLogger(__name__)

_TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilyWebSearchService:
    """Thin wrapper around the Tavily Search API.

    Fail-open: returns an empty list when the API key is absent, web search
    is disabled, or any network / API error occurs.
    """

    def __init__(self) -> None:
        self._api_key: str | None = settings.tavily_api_key
        self._enabled: bool = settings.web_search_active()
        self._search_depth: str = settings.tavily_search_depth
        self._max_results: int = settings.tavily_max_results

    @traceable_if_enabled(
        name="web_search",
        run_type="tool",
        process_inputs=process_web_search_inputs,
        process_outputs=process_web_search_outputs,
    )
    async def search(self, query: str) -> list[dict[str, Any]]:
        if not self._enabled or not self._api_key:
            logger.debug("Web search skipped (disabled or no API key)")
            return []

        payload = {
            "api_key": self._api_key,
            "query": query,
            "search_depth": self._search_depth,
            "max_results": self._max_results,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(_TAVILY_SEARCH_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            logger.exception("Tavily web search failed for query=%r", query)
            return []

        results: list[dict[str, Any]] = []
        for item in data.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                }
            )
        return results
