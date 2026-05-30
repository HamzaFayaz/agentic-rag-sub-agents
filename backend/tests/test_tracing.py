"""Smoke tests for LangSmith tracing helpers."""

from unittest.mock import patch

import pytest

from app.services import tracing


def test_tracing_disabled_is_noop_decorator():
    @tracing.traceable_if_enabled(name="noop_test")
    def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5


def test_tracing_enabled_sets_env_and_decorates():
    with patch.object(tracing.settings, "langsmith_tracing", True):
        with patch.object(tracing.settings, "langsmith_api_key", "test-key"):
            with patch.dict("os.environ", {}, clear=True):
                tracing.ensure_langsmith_env()
                assert tracing.tracing_enabled()
                assert tracing.os.environ.get("LANGSMITH_API_KEY") == "test-key"
                assert tracing.os.environ.get("LANGSMITH_TRACING") == "true"

                @tracing.traceable_if_enabled(name="enabled_test")
                def mul(a: int, b: int) -> int:
                    return a * b

                assert mul.__name__ == "mul"
                assert mul(3, 4) == 12


def test_content_for_trace_snippet_mode():
    with patch.object(tracing.settings, "langsmith_log_chunk_text", False):
        long_text = "x" * 300
        assert tracing.content_for_trace(long_text).endswith("…")
        assert len(tracing.content_for_trace(long_text)) == 201


def test_content_for_trace_full_mode():
    with patch.object(tracing.settings, "langsmith_log_chunk_text", True):
        long_text = "x" * 300
        assert tracing.content_for_trace(long_text) == long_text
