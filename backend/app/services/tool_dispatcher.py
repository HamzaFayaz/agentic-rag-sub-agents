"""Route tool calls from the LLM to the correct executor.

ToolDispatcher is the single entry-point used by the agent loop.
It checks feature-gate settings before dispatching so disabled tools
are rejected early with a user-friendly message.
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import Settings
from app.services.retrieval import RetrievalService
from app.services.tool_executor import (
    execute_query_database,
    execute_search_documents,
    execute_web_search,
)

logger = logging.getLogger(__name__)

KNOWN_TOOLS = frozenset({"search_documents", "query_database", "web_search"})


class ToolDispatcher:
    """Dispatch ``tool_name`` + ``args`` to the matching executor."""

    def __init__(
        self,
        settings: Settings,
        retrieval_service: RetrievalService,
    ) -> None:
        self._settings = settings
        self._retrieval = retrieval_service

    async def dispatch(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute *tool_name* with *args* and return a result dict.

        Raises
        ------
        ValueError
            If *tool_name* is unknown or its feature gate is disabled.
        """
        if tool_name not in KNOWN_TOOLS:
            raise ValueError(f"Unknown tool: {tool_name}")

        if tool_name == "search_documents":
            return await execute_search_documents(
                query=args["query"],
                retrieval_service=self._retrieval,
            )

        if tool_name == "query_database":
            if not self._settings.text_to_sql_active():
                raise ValueError(
                    "query_database is disabled — "
                    "set TEXT_TO_SQL_ENABLED=true and DATABASE_URL to activate"
                )
            return await execute_query_database(
                question=args["question"],
                sql=args["sql"],
            )

        if tool_name == "web_search":
            if not self._settings.web_search_active():
                raise ValueError(
                    "web_search is disabled — "
                    "set WEB_SEARCH_ENABLED=true and TAVILY_API_KEY to activate"
                )
            return await execute_web_search(query=args["query"])

        raise ValueError(f"Unhandled tool: {tool_name}")
