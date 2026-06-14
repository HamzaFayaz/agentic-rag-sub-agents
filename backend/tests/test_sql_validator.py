"""Tests for the read-only SQL validator."""

from __future__ import annotations

import pytest

from app.services.sql_validator import SqlValidationError, validate_sql


class TestValidQueries:
    def test_select_count_from_view(self):
        result = validate_sql("SELECT COUNT(*) FROM v_user_document_stats")
        assert "v_user_document_stats" in result
        assert "LIMIT" in result

    def test_select_star_from_view(self):
        result = validate_sql("SELECT * FROM v_user_chunk_meta")
        assert "v_user_chunk_meta" in result

    def test_join_across_allowed_views(self):
        sql = (
            "SELECT d.filename, c.chunk_index "
            "FROM v_user_document_stats d "
            "JOIN v_user_chunk_meta c ON c.document_id = d.id"
        )
        result = validate_sql(sql)
        assert "LIMIT" in result

    def test_existing_limit_preserved(self):
        sql = "SELECT * FROM v_user_document_stats LIMIT 10"
        result = validate_sql(sql)
        assert result.count("LIMIT") == 1
        assert "LIMIT 10" in result

    def test_chat_stats_view(self):
        result = validate_sql("SELECT thread_count FROM v_user_chat_stats")
        assert "v_user_chat_stats" in result


class TestRejections:
    def test_content_column_in_select(self):
        with pytest.raises(SqlValidationError, match="blocked identifier"):
            validate_sql("SELECT content FROM v_user_chunk_meta")

    def test_raw_table_document_chunks(self):
        with pytest.raises(SqlValidationError, match="blocked identifier"):
            validate_sql("SELECT * FROM document_chunks")

    def test_raw_table_documents(self):
        with pytest.raises(SqlValidationError, match="blocked identifier"):
            validate_sql("SELECT * FROM documents")

    def test_delete_rejected(self):
        with pytest.raises(SqlValidationError, match="Write"):
            validate_sql("DELETE FROM v_user_document_stats WHERE id = 1")

    def test_drop_rejected(self):
        with pytest.raises(SqlValidationError, match="Write"):
            validate_sql("DROP TABLE v_user_document_stats")

    def test_insert_rejected(self):
        with pytest.raises(SqlValidationError, match="Write"):
            validate_sql("INSERT INTO v_user_document_stats (id) VALUES (1)")

    def test_multiple_statements_rejected(self):
        with pytest.raises(SqlValidationError, match="single"):
            validate_sql(
                "SELECT 1 FROM v_user_document_stats; "
                "SELECT 2 FROM v_user_chunk_meta"
            )

    def test_empty_sql_rejected(self):
        with pytest.raises(SqlValidationError, match="Empty"):
            validate_sql("")

    def test_unknown_table_rejected(self):
        with pytest.raises(SqlValidationError, match="not in allowlist"):
            validate_sql("SELECT * FROM users")
