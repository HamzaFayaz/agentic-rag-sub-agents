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
from app.services.sub_agent import ProgressCallback
from app.services.tool_executor import (
    execute_analyze_document,
    execute_query_database,
    execute_search_documents,
    execute_web_search,
)

logger = logging.getLogger(__name__)

KNOWN_TOOLS = frozenset(
    {"search_documents", "query_database", "web_search", "analyze_document"}
)


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
        *,
        user_jwt: str | None = None,
        on_subagent_progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Execute *tool_name* with *args* and return a result dict.

        Parameters
        ----------
        user_jwt
            Required for ``query_database`` (RLS binding). Ignored by
            other tools.

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
            if not user_jwt:
                raise ValueError(
                    "query_database requires a user JWT for RLS binding"
                )
            return await execute_query_database(
                question=args["question"],
                sql=args["sql"],
                user_jwt=user_jwt,
            )

        if tool_name == "web_search":
            if not self._settings.web_search_active():
                raise ValueError(
                    "web_search is disabled — "
                    "set WEB_SEARCH_ENABLED=true and TAVILY_API_KEY to activate"
                )
            return await execute_web_search(query=args["query"])

        if tool_name == "analyze_document":
            if not self._settings.sub_agent_active():
                raise ValueError(
                    "analyze_document is disabled — "
                    "set SUB_AGENT_ENABLED=true to activate"
                )
            if not user_jwt:
                raise ValueError(
                    "analyze_document requires a user JWT for document access"
                )
            return await execute_analyze_document(
                filename=args["filename"],
                task=args["task"],
                user_jwt=user_jwt,
                on_progress=on_subagent_progress,
            )

        raise ValueError(f"Unhandled tool: {tool_name}")
