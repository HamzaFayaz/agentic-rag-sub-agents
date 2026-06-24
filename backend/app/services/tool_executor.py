"""Individual tool executor functions for the multi-tool agent.

Each function takes tool-specific args, runs the underlying service,
and returns a plain dict matching the corresponding ToolResult model.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

from app.services.retrieval import RetrievalService
from app.services.sql_validator import SqlValidationError
from app.services.sub_agent import DocumentAnalystService, ProgressCallback
from app.services.supabase_client import SupabaseRepository
from app.services.text_to_sql import TextToSqlService

logger = logging.getLogger(__name__)

_sql_service = TextToSqlService()
_analyst_service = DocumentAnalystService()


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


async def execute_analyze_document(
    filename: str,
    task: str,
    user_jwt: str,
    *,
    on_progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Resolve filename and run the document analyst sub-agent."""
    repo = SupabaseRepository(user_jwt)
    matches = repo.find_documents_by_filename(filename)

    if not matches:
        available = repo.list_ready_filenames()
        hint = ", ".join(available[:10]) if available else "(no ready documents)"
        return {
            "error": (
                f"Document '{filename}' not found. Available files: {hint}"
            ),
            "report": "",
            "mode": "single_pass",
            "passes": 0,
            "document_id": "",
            "filename": filename,
        }

    if len(matches) > 1:
        names = ", ".join(m["filename"] for m in matches)
        return {
            "error": f"Ambiguous filename '{filename}'. Matches: {names}",
            "report": "",
            "mode": "single_pass",
            "passes": 0,
            "document_id": "",
            "filename": filename,
        }

    doc = matches[0]
    if doc.get("status") != "ready":
        return {
            "error": f"Document '{doc['filename']}' is not ready (status: {doc.get('status')}).",
            "report": "",
            "mode": "single_pass",
            "passes": 0,
            "document_id": str(doc.get("id", "")),
            "filename": doc.get("filename", filename),
        }

    try:
        report = await _analyst_service.analyze(
            document_id=UUID(str(doc["id"])),
            filename=str(doc["filename"]),
            task=task,
            user_jwt=user_jwt,
            on_progress=on_progress,
        )
        return report.model_dump()
    except Exception as exc:
        logger.exception("Document analyst failed for %s", filename)
        return {
            "error": str(exc),
            "report": "",
            "mode": "single_pass",
            "passes": 0,
            "document_id": str(doc.get("id", "")),
            "filename": doc.get("filename", filename),
        }
