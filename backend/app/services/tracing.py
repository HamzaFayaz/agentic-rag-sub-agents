"""LangSmith tracing helpers — no-ops when tracing is disabled."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, TypeVar

from openai import AsyncOpenAI

from app.config import settings

F = TypeVar("F", bound=Callable[..., Any])


def tracing_enabled() -> bool:
    return bool(settings.langsmith_tracing and settings.langsmith_api_key)


def ensure_langsmith_env() -> None:
    if not tracing_enabled():
        return
    os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key or "")
    os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_TRACING_V2", "true")


def traceable_if_enabled(**trace_kwargs: Any) -> Callable[[F], F]:
    """Return ``@traceable(...)`` when tracing is on, else an identity decorator."""

    def decorator(fn: F) -> F:
        if not tracing_enabled():
            return fn
        ensure_langsmith_env()
        from langsmith.run_helpers import traceable

        return traceable(**trace_kwargs)(fn)  # type: ignore[return-value]

    return decorator


def build_traced_openai_client() -> AsyncOpenAI:
    ensure_langsmith_env()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    if tracing_enabled():
        from langsmith.wrappers import wrap_openai

        return wrap_openai(client)
    return client


def content_for_trace(text: str) -> str:
    if settings.langsmith_log_chunk_text:
        return text
    if len(text) <= 200:
        return text
    return text[:200] + "…"


def retrieved_sources_trace_output(
    sources: list[Any],
    hits: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    hit_by_doc: dict[str, str] = {}
    if hits:
        for hit in hits:
            doc_id = str(hit.get("document_id") or "")
            chunk_id = str(hit.get("id") or "")
            if doc_id and chunk_id:
                hit_by_doc[doc_id] = chunk_id

    rows: list[dict[str, Any]] = []
    for source in sources:
        snippet = getattr(source, "snippet", "") or ""
        rows.append(
            {
                "document_id": getattr(source, "document_id", ""),
                "chunk_id": hit_by_doc.get(getattr(source, "document_id", ""), ""),
                "filename": getattr(source, "filename", ""),
                "similarity": getattr(source, "similarity", 0.0),
                "snippet": content_for_trace(snippet),
            }
        )
    return rows


def process_chat_turn_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "thread_id": str(inputs.get("thread_id", "")),
        "query": inputs.get("content", ""),
    }


def process_chat_turn_outputs(output: Any) -> dict[str, Any]:
    sources = getattr(output, "sources", None) or []
    return {
        "source_count": len(sources),
        "has_context": len(sources) > 0,
    }


def process_rag_retrieve_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    return {"query": inputs.get("query", "")}


def process_rag_retrieve_outputs(output: Any) -> dict[str, Any]:
    if not isinstance(output, tuple) or len(output) != 2:
        return {"sources": [], "chunk_count": 0}
    _context_blocks, sources = output
    return {
        "chunk_count": len(sources),
        "sources": [
            {
                "chunk_id": getattr(s, "chunk_id", "") or "",
                "document_id": s.document_id,
                "filename": s.filename,
                "similarity": s.similarity,
                "snippet": content_for_trace(s.snippet),
            }
            for s in sources
        ],
    }


def process_hybrid_rrf_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    vector_hits = inputs.get("vector_hits") or []
    keyword_hits = inputs.get("keyword_hits") or []
    return {
        "vector_count": len(vector_hits),
        "keyword_count": len(keyword_hits),
    }


def process_hybrid_rrf_outputs(output: Any) -> dict[str, Any]:
    merged = output or []
    return {
        "candidate_count": len(merged),
        "top_ids": [str(hit.get("id", "")) for hit in merged[:10]],
    }


def process_cohere_rerank_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    documents = inputs.get("documents") or []
    return {
        "query": inputs.get("query", ""),
        "candidate_count": len(documents),
    }


def process_cohere_rerank_outputs(output: Any) -> dict[str, Any]:
    if isinstance(output, dict):
        return {
            "top_indices": output.get("top_indices", []),
            "scores": output.get("scores", []),
        }
    return {"top_indices": list(output or [])}


def process_build_rag_prompt_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    blocks = inputs.get("context_blocks") or []
    return {"chunk_count": len(blocks)}


def process_build_rag_prompt_outputs(output: Any) -> dict[str, Any]:
    system_content = str(output or "")
    result: dict[str, Any] = {"system_length": len(system_content)}
    if settings.langsmith_log_chunk_text:
        result["preview"] = content_for_trace(system_content)
    return result


def process_metadata_extract_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    parser_meta = inputs.get("parser_meta") or {}
    headings = parser_meta.get("heading_count")
    if headings is None:
        headings = parser_meta.get("headings")
    heading_count = len(headings) if isinstance(headings, list) else headings
    return {
        "filename": inputs.get("filename", ""),
        "heading_count": heading_count,
    }


def process_metadata_extract_outputs(output: Any) -> dict[str, Any]:
    if output is None:
        return {"metadata_llm": None}
    if isinstance(output, dict):
        return {"metadata_llm": output}
    if hasattr(output, "model_dump"):
        return {"metadata_llm": output.model_dump(mode="json")}
    return {"metadata_llm": output}


def process_document_ingest_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    digest = str(inputs.get("digest") or "")
    return {
        "filename": inputs.get("filename", ""),
        "hash_prefix": digest[:12] if digest else None,
    }


def process_document_ingest_outputs(output: Any) -> dict[str, Any]:
    if not isinstance(output, dict):
        return {}
    metadata = output.get("metadata") or {}
    parser = metadata.get("parser") or {}
    return {
        "status": output.get("status"),
        "chunk_strategy": parser.get("chunk_strategy"),
        "chunk_count": parser.get("chunk_count"),
    }


def process_embed_texts_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    texts = inputs.get("texts") or []
    total_chars = sum(len(t) for t in texts)
    payload: dict[str, Any] = {
        "count": len(texts),
        "total_char_length": total_chars,
    }
    if settings.langsmith_log_chunk_text:
        payload["texts"] = [content_for_trace(t) for t in texts]
    else:
        payload["query_length"] = total_chars if len(texts) == 1 else None
    return payload


def process_embed_texts_outputs(_output: Any) -> dict[str, Any]:
    return {"model": settings.openai_embedding_model}


def process_query_database_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    sql = str(inputs.get("sql") or "")
    return {"sql_preview": content_for_trace(sql)}


def process_query_database_outputs(output: Any) -> dict[str, Any]:
    if not isinstance(output, dict):
        return {}
    return {
        "row_count": output.get("row_count", 0),
        "sql": content_for_trace(str(output.get("sql") or "")),
    }


def process_web_search_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    return {"query": inputs.get("query", "")}


def process_web_search_outputs(output: Any) -> dict[str, Any]:
    if not isinstance(output, list):
        return {"result_count": 0}
    return {
        "result_count": len(output),
        "urls": [str(item.get("url", "")) for item in output[:5] if isinstance(item, dict)],
    }


def process_document_analyze_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": str(inputs.get("document_id", "")),
        "filename": inputs.get("filename", ""),
        "task": content_for_trace(str(inputs.get("task") or "")),
    }


def process_document_analyze_outputs(output: Any) -> dict[str, Any]:
    if hasattr(output, "model_dump"):
        data = output.model_dump()
    elif isinstance(output, dict):
        data = output
    else:
        return {}
    return {
        "mode": data.get("mode"),
        "passes": data.get("passes"),
        "filename": data.get("filename"),
        "report_length": len(str(data.get("report") or "")),
    }


@traceable_if_enabled(
    name="build_rag_prompt",
    run_type="chain",
    process_inputs=process_build_rag_prompt_inputs,
    process_outputs=process_build_rag_prompt_outputs,
)
def build_traced_rag_system_prompt(context_blocks: list[str]) -> str:
    return settings.build_rag_system_prompt(context_blocks)
