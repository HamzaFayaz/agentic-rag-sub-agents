"""Individual tool executor functions for the multi-tool agent.

Each function takes tool-specific args, runs the underlying service,
and returns a plain dict matching the corresponding ToolResult model.
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.retrieval import RetrievalService

logger = logging.getLogger(__name__)


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
    **_kwargs: Any,
) -> dict[str, Any]:
    """Execute a read-only SQL query against metadata views.

    Placeholder until Track A wires up the text-to-SQL pipeline.
    """
    raise NotImplementedError(
        "query_database is not yet implemented — waiting for Track A SQL executor"
    )


async def execute_web_search(
    query: str,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Search the public web via Tavily.

    Placeholder until Track B wires up the web-search integration.
    """
    raise NotImplementedError(
        "web_search is not yet implemented — waiting for Track B web executor"
    )
