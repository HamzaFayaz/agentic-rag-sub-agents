"""Tests for OpenAI tool-calling helpers (E-T1)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.openai_client import OpenAIClient, parse_tool_calls


def _make_tool_call(
    tc_id: str = "call_abc",
    name: str = "search_documents",
    arguments: dict | None = None,
) -> MagicMock:
    tc = MagicMock()
    tc.id = tc_id
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments or {"query": "hello"})
    return tc


def _make_completion(
    tool_calls: list | None = None,
    finish_reason: str = "tool_calls",
    content: str | None = None,
) -> MagicMock:
    choice = MagicMock()
    choice.finish_reason = finish_reason
    choice.message.tool_calls = tool_calls
    choice.message.content = content
    completion = MagicMock()
    completion.choices = [choice]
    return completion


class TestParseToolCalls:
    def test_single_tool_call(self):
        tc = _make_tool_call(name="search_documents", arguments={"query": "test"})
        completion = _make_completion(tool_calls=[tc])

        result = parse_tool_calls(completion)

        assert len(result) == 1
        assert result[0]["id"] == "call_abc"
        assert result[0]["name"] == "search_documents"
        assert result[0]["arguments"] == {"query": "test"}

    def test_multiple_tool_calls(self):
        tc1 = _make_tool_call(tc_id="call_1", name="search_documents", arguments={"query": "a"})
        tc2 = _make_tool_call(tc_id="call_2", name="web_search", arguments={"query": "b"})
        completion = _make_completion(tool_calls=[tc1, tc2])

        result = parse_tool_calls(completion)

        assert len(result) == 2
        assert result[0]["name"] == "search_documents"
        assert result[1]["name"] == "web_search"

    def test_no_tool_calls_stop_finish(self):
        completion = _make_completion(tool_calls=None, finish_reason="stop")

        result = parse_tool_calls(completion)

        assert result == []

    def test_malformed_arguments_returns_empty_dict(self):
        tc = _make_tool_call()
        tc.function.arguments = "not-json{{"
        completion = _make_completion(tool_calls=[tc])

        result = parse_tool_calls(completion)

        assert len(result) == 1
        assert result[0]["arguments"] == {}


class TestCreateChatWithTools:
    @pytest.mark.asyncio
    async def test_calls_openai_with_tools(self):
        client = OpenAIClient.__new__(OpenAIClient)

        mock_inner = AsyncMock()
        expected_completion = _make_completion(
            tool_calls=[_make_tool_call()],
        )
        mock_inner.chat.completions.create = AsyncMock(return_value=expected_completion)
        client._client = mock_inner

        messages = [{"role": "user", "content": "hi"}]
        tools = [{"type": "function", "function": {"name": "search_documents"}}]

        result = await client.create_chat_with_tools(messages, tools)

        mock_inner.chat.completions.create.assert_awaited_once()
        call_kwargs = mock_inner.chat.completions.create.call_args.kwargs
        assert call_kwargs["tools"] == tools
        assert call_kwargs["messages"] == messages
        assert "stream" not in call_kwargs
        assert result is expected_completion
