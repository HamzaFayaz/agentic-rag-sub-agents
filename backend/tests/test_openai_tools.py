"""Tests for OpenAI tool-calling helpers."""

from __future__ import annotations

from openai.types.chat import ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call import Function

from app.services.openai_client import parse_tool_calls


def test_parse_tool_calls_extracts_name_and_arguments():
    tool_calls = [
        ChatCompletionMessageToolCall(
            id="call_abc",
            type="function",
            function=Function(
                name="search_documents",
                arguments='{"query": "python skills"}',
            ),
        )
    ]

    parsed = parse_tool_calls(tool_calls)

    assert len(parsed) == 1
    assert parsed[0].id == "call_abc"
    assert parsed[0].name == "search_documents"
    assert parsed[0].arguments == {"query": "python skills"}


def test_parse_tool_calls_empty_when_none():
    assert parse_tool_calls(None) == []


def test_parse_tool_calls_handles_invalid_json():
    tool_calls = [
        ChatCompletionMessageToolCall(
            id="call_bad",
            type="function",
            function=Function(name="query_database", arguments="not-json"),
        )
    ]

    parsed = parse_tool_calls(tool_calls)

    assert len(parsed) == 1
    assert parsed[0].name == "query_database"
    assert parsed[0].arguments == {}
