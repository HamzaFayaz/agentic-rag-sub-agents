"""Tests for TextToSqlService (mocked DB, real validator)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest

from app.services.sql_validator import SqlValidationError
from app.services.text_to_sql import TextToSqlService, _extract_sub


FAKE_JWT = pyjwt.encode(
    {"sub": "user-123", "exp": 9999999999},
    "test-secret",
    algorithm="HS256",
)
NO_SUB_JWT = pyjwt.encode(
    {"exp": 9999999999},
    "test-secret",
    algorithm="HS256",
)


class TestExtractSub:
    def test_returns_sub_from_jwt(self):
        assert _extract_sub(FAKE_JWT) == "user-123"

    def test_raises_on_missing_sub(self):
        with pytest.raises(ValueError, match="sub"):
            _extract_sub(NO_SUB_JWT)


class TestTextToSqlServiceValidation:
    """Validation errors should propagate without touching the DB."""

    @pytest.mark.asyncio
    async def test_rejects_write_query(self):
        svc = TextToSqlService()
        with pytest.raises(SqlValidationError, match="Write"):
            await svc.execute("DELETE FROM v_user_document_stats", FAKE_JWT)

    @pytest.mark.asyncio
    async def test_rejects_blocked_table(self):
        svc = TextToSqlService()
        with pytest.raises(SqlValidationError, match="blocked identifier"):
            await svc.execute("SELECT * FROM document_chunks", FAKE_JWT)


class TestTextToSqlServiceExecution:
    """Happy-path execution with mocked asyncpg pool."""

    @pytest.mark.asyncio
    async def test_execute_returns_rows(self):
        fake_records = [
            {"id": "abc", "filename": "cv.pdf", "chunk_count": 12},
            {"id": "def", "filename": "handbook.pdf", "chunk_count": 7},
        ]
        mock_records = []
        for row in fake_records:
            rec = MagicMock()
            rec.__iter__ = MagicMock(return_value=iter(row.items()))
            rec.items = MagicMock(return_value=row.items())
            rec.keys = MagicMock(return_value=row.keys())
            rec.__getitem__ = MagicMock(side_effect=row.__getitem__)
            mock_records.append(rec)

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_records)
        mock_conn.execute = AsyncMock()

        mock_tx = AsyncMock()
        mock_tx.__aenter__ = AsyncMock(return_value=mock_tx)
        mock_tx.__aexit__ = AsyncMock(return_value=False)
        mock_conn.transaction = MagicMock(return_value=mock_tx)

        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_conn_ctx)

        with patch("app.services.text_to_sql.get_pool", return_value=mock_pool):
            svc = TextToSqlService()
            result = await svc.execute(
                "SELECT * FROM v_user_document_stats",
                FAKE_JWT,
            )

        assert result["row_count"] == 2
        assert "LIMIT" in result["sql"]
        assert mock_conn.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_sets_rls_claims(self):
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.execute = AsyncMock()

        mock_tx = AsyncMock()
        mock_tx.__aenter__ = AsyncMock(return_value=mock_tx)
        mock_tx.__aexit__ = AsyncMock(return_value=False)
        mock_conn.transaction = MagicMock(return_value=mock_tx)

        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_conn_ctx)

        with patch("app.services.text_to_sql.get_pool", return_value=mock_pool):
            svc = TextToSqlService()
            await svc.execute(
                "SELECT COUNT(*) FROM v_user_chat_stats",
                FAKE_JWT,
            )

        execute_calls = [str(c) for c in mock_conn.execute.call_args_list]
        joined = " ".join(execute_calls)
        assert "statement_timeout" in joined
        assert "authenticated" in joined
        assert "user-123" in joined
