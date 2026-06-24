"""Module 7 tool schemas, SSE payloads, and shared SQL allowlist hints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.config import Settings

ALLOWLIST_VIEWS: tuple[str, ...] = (
    "v_user_document_stats",
    "v_user_chunk_meta",
    "v_user_chat_stats",
)

SQL_SCHEMA_HINT = (
    "Query ONLY these views and columns:\n"
    "  v_user_document_stats → id, filename, status, mime_type, byte_size, "
    "created_at, metadata, chunk_count, total_token_count\n"
    "  v_user_chunk_meta → id, document_id, chunk_index, section_title, "
    "heading_level, chunk_level, token_count\n"
    "  v_user_chat_stats → thread_count, message_count, latest_thread_at, "
    "latest_message_at\n"
    "Use for counts, lists, filters, aggregates.\n"
    "For what documents say, use search_documents."
)


class ToolStartEvent(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


class ToolEndEvent(BaseModel):
    tool: str
    status: Literal["success", "error"]
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class DocumentToolResult(BaseModel):
    context_blocks: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)


class SqlToolResult(BaseModel):
    sql: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0


class WebToolResult(BaseModel):
    results: list[dict[str, str]] = Field(default_factory=list)


class AnalystToolResult(BaseModel):
    report: str
    mode: Literal["single_pass", "multi_pass"]
    passes: int
    document_id: str
    filename: str


def _search_documents_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Hybrid search over the user's uploaded documents. Use when the "
                "answer is inside document prose — policies, CV skills, handbook "
                "sections, etc. Returns relevant excerpts with source filenames."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query describing what to find in documents.",
                    },
                },
                "required": ["query"],
            },
        },
    }


def _query_database_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": (
                "Run a read-only SELECT on the user's library metadata. "
                f"{SQL_SCHEMA_HINT}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The user's question in plain English.",
                    },
                    "sql": {
                        "type": "string",
                        "description": "A single read-only SELECT query using allowlisted views only.",
                    },
                },
                "required": ["question", "sql"],
            },
        },
    }


def _web_search_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the public web for current or external information not in "
                "the user's documents or database. Use when the user asks to search "
                "online, wants latest news, or needs external facts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Web search query.",
                    },
                },
                "required": ["query"],
            },
        },
    }


def _analyze_document_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "analyze_document",
            "description": (
                "Deep-read or summarize a whole uploaded document by filename. "
                "Use for full-document summaries, comprehensive reviews, or when "
                "comparing two specific files — call this tool once per file in "
                "the same step so analyses run in parallel. NOT for pinpoint "
                "facts; use search_documents for targeted excerpts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Exact filename of the document in the user's library.",
                    },
                    "task": {
                        "type": "string",
                        "description": (
                            "What to extract or summarize from the document "
                            "(e.g. summarize key policies, compare terms)."
                        ),
                    },
                },
                "required": ["filename", "task"],
            },
        },
    }


def build_available_tools(settings: Settings) -> list[dict[str, Any]]:
    """Return OpenAI tool definitions for enabled tools only."""
    tools: list[dict[str, Any]] = [_search_documents_tool()]

    if settings.text_to_sql_active():
        tools.append(_query_database_tool())

    if settings.web_search_active():
        tools.append(_web_search_tool())

    if settings.sub_agent_active():
        tools.append(_analyze_document_tool())

    return tools
