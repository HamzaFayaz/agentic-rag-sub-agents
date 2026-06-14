"""Read-only SQL validator with allowlist enforcement.

Parses incoming SQL, rejects writes / DDL / raw-table access, and
injects a LIMIT clause when missing.
"""

from __future__ import annotations

import re

import sqlparse
from sqlparse.tokens import DML, Keyword

from app.config import settings
from app.services.tool_contracts import ALLOWLIST_VIEWS

_BLOCKED_IDENTIFIERS_RE = re.compile(
    r"\b(content|embedding|document_chunks|documents)\b",
    re.IGNORECASE,
)

_WRITE_KEYWORDS_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|COPY)\b",
    re.IGNORECASE,
)

_LIMIT_RE = re.compile(r"\bLIMIT\s+\d+", re.IGNORECASE)


class SqlValidationError(Exception):
    """Raised when a SQL string fails safety checks."""


def _extract_table_names(parsed: sqlparse.sql.Statement) -> set[str]:
    """Return table / view names referenced after FROM / JOIN keywords."""
    names: set[str] = set()
    expect_table = False
    for token in parsed.flatten():
        if token.ttype is Keyword and (
            token.normalized == "FROM" or "JOIN" in token.normalized
        ):
            expect_table = True
            continue
        if expect_table:
            if token.ttype is sqlparse.tokens.Name:
                names.add(token.value.lower())
                expect_table = False
            elif token.ttype not in (
                sqlparse.tokens.Whitespace,
                sqlparse.tokens.Newline,
            ):
                expect_table = False
    return names


def validate_sql(sql: str, *, row_limit: int | None = None) -> str:
    """Validate *sql* and return it with a LIMIT clause injected if absent.

    Raises ``SqlValidationError`` on any safety violation.
    """
    sql = sql.strip().rstrip(";")
    if not sql:
        raise SqlValidationError("Empty SQL statement")

    if _WRITE_KEYWORDS_RE.search(sql):
        raise SqlValidationError("Write / DDL operations are not allowed")

    blocked_match = _BLOCKED_IDENTIFIERS_RE.search(sql)
    if blocked_match:
        raise SqlValidationError(
            f"Access denied — reference to blocked identifier: {blocked_match.group()}"
        )

    statements = sqlparse.parse(sql)
    if len(statements) != 1:
        raise SqlValidationError("Only a single SQL statement is allowed")

    stmt = statements[0]

    first_token = stmt.token_first(skip_cm=True, skip_ws=True)
    if (
        first_token is None
        or first_token.ttype is not DML
        or first_token.normalized != "SELECT"
    ):
        raise SqlValidationError("Only SELECT statements are allowed")

    tables = _extract_table_names(stmt)
    non_allowed = tables - set(ALLOWLIST_VIEWS)
    if non_allowed:
        raise SqlValidationError(
            f"Table(s) not in allowlist: {', '.join(sorted(non_allowed))}"
        )

    limit = row_limit if row_limit is not None else settings.sql_row_limit
    if not _LIMIT_RE.search(sql):
        sql = f"{sql}\nLIMIT {limit}"

    return sql
