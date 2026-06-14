"""Individual tool executor functions for the multi-tool agent.

Each function takes tool-specific args, runs the underlying service,
and returns a plain dict matching the corresponding ToolResult model.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.retrieval import RetrievalService
from app.services.sql_validator import SqlValidationError
from app.services.text_to_sql import TextToSqlService

logger = logging.getLogger(__name__)

_sql_service = TextToSqlService()


async def execute_search_documents(
    query: str,
    retrieval_service: RetrievalService,
) -> dict[str, Any]:
    """Run hybrid RAG retrieval and return a DocumentToolResult-shaped dict.

    Tracing is handled inside ``RetrievalService.retrieve`` via the
    ``@traceable_if_enabled(name="rag_retrieve")`` decorator, so callers
    inherit LangSmith spans automatically.
    """
    context_blocks, sources = await retrieval_service.retrieve(query)
    return {
        "context_blocks": context_blocks,
        "sources": [s.to_dict() for s in sources],
    }


async def execute_query_database(
    question: str,
    sql: str,
    user_jwt: str,
) -> dict[str, Any]:
    """Execute a read-only SQL query against metadata views.

    Returns a SqlToolResult-shaped dict with an extra ``content`` field
    containing a JSON-formatted string for the LLM tool message.
    """
    try:
        result = await _sql_service.execute(sql, user_jwt)
    except SqlValidationError as exc:
        logger.warning("SQL validation failed: %s", exc)
        return {
            "sql": sql,
            "rows": [],
            "row_count": 0,
            "error": str(exc),
            "content": f"SQL validation error: {exc}",
        }
    except Exception as exc:
        logger.exception("SQL execution failed")
        return {
            "sql": sql,
            "rows": [],
            "row_count": 0,
            "error": str(exc),
            "content": f"Database query error: {exc}",
        }

    result["content"] = json.dumps(result["rows"], default=str)
    return result


async def execute_web_search(
    query: str,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Search the public web via Tavily and return a WebToolResult-shaped dict."""
    from app.services.web_search import TavilyWebSearchService

    svc = TavilyWebSearchService()
    raw_results = await svc.search(query)

    formatted: list[dict[str, str]] = []
    for item in raw_results:
        formatted.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
            }
        )

    return {"results": formatted}
