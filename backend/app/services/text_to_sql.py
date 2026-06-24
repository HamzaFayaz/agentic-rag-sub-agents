"""Text-to-SQL execution service with RLS-aware session binding."""

from __future__ import annotations

import json
import logging
from typing import Any

import jwt

from app.config import settings
from app.services.db import get_pool
from app.services.sql_validator import SqlValidationError, validate_sql
from app.services.tracing import (
    process_query_database_inputs,
    process_query_database_outputs,
    traceable_if_enabled,
)

logger = logging.getLogger(__name__)


def _extract_sub(user_jwt: str) -> str:
    """Decode JWT without verification to extract the ``sub`` claim."""
    payload = jwt.decode(user_jwt, options={"verify_signature": False})
    sub = payload.get("sub")
    if not sub:
        raise ValueError("JWT does not contain a 'sub' claim")
    return sub


class TextToSqlService:
    """Validate, bind RLS context, and execute a read-only SQL query."""

    @traceable_if_enabled(
        name="query_database",
        run_type="tool",
        process_inputs=process_query_database_inputs,
        process_outputs=process_query_database_outputs,
    )
    async def execute(
        self,
        sql: str,
        user_jwt: str,
    ) -> dict[str, Any]:
        """Run *sql* as the user identified by *user_jwt*.

        Returns a ``SqlToolResult``-shaped dict with ``sql``, ``rows``,
        and ``row_count``.
        """
        validated_sql = validate_sql(sql)

        sub = _extract_sub(user_jwt)
        claims_json = json.dumps({"sub": sub})
        timeout_ms = settings.sql_query_timeout_sec * 1000

        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                await conn.execute(
                    f"SET LOCAL statement_timeout = {timeout_ms}"
                )
                await conn.execute(
                    "SET LOCAL role = 'authenticated'"
                )
                await conn.execute(
                    f"SET LOCAL request.jwt.claims = {asyncpg_literal(claims_json)}"
                )
                records = await conn.fetch(validated_sql)

            rows = [dict(r) for r in records]
            return {
                "sql": validated_sql,
                "rows": rows,
                "row_count": len(rows),
            }


def asyncpg_literal(value: str) -> str:
    """Escape a string as a single-quoted SQL literal for SET LOCAL."""
    escaped = value.replace("'", "''")
    return f"'{escaped}'"
