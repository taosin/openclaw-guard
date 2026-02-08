"""Unit tests for core.proxy."""
import json
from unittest.mock import MagicMock, patch

import pytest

from core.proxy import (
    _count_message_tokens,
    _extract_tool_calls_from_body,
    _get_tool_call_command,
    _inject_error_message,
    _response_with_error,
    _set_tool_call_command,
    guard_request,
    guard_response,
)


class TestCountMessageTokens:
    """Tests for _count_message_tokens."""

    def test_string(self):
        with patch("core.proxy.estimate_tokens", return_value=10):
            assert _count_message_tokens("hello") == 10

    def test_dict(self):
        with patch("core.proxy.estimate_tokens", return_value=5):
            assert _count_message_tokens({"a": "x", "b": "y"}) == 10

    def test_list(self):
        with patch("core.proxy.estimate_tokens", return_value=3):
            assert _count_message_tokens(["a", "b"]) == 6

    def test_non_string_dict_value(self):
        with patch("core.proxy.estimate_tokens", return_value=0):
            assert _count_message_tokens({"n": 42}) == 0


class TestExtractToolCallsFromBody:
    """Tests for _extract_tool_calls_from_body."""

    def test_empty_body(self):
        assert _extract_tool_calls_from_body({}) == []
        assert _extract_tool_calls_from_body({"messages": []}) == []

    def test_from_messages(self):
        tc = {"id": "1", "function": {"name": "run_shell", "arguments": "{}"}}
        body = {"messages": [{"role": "assistant", "tool_calls": [tc]}]}
        got = _extract_tool_calls_from_body(body)
        assert len(got) == 1
        assert got[0]["id"] == "1"

    def test_from_choices(self):
        tc = {"id": "2", "function": {"name": "run_command", "arguments": "{}"}}
        body = {"choices": [{"message": {"tool_calls": [tc]}}]}
        got = _extract_tool_calls_from_body(body)
        assert len(got) == 1
        assert got[0]["id"] == "2"


class TestGetToolCallCommand:
    """Tests for _get_tool_call_command."""

    def test_command_in_args_string(self):
        tc = {"function": {"arguments": json.dumps({"command": "ls -la"})}}
        assert _get_tool_call_command(tc) == "ls -la"

    def test_cmd_in_args_string(self):
        tc = {"function": {"arguments": json.dumps({"cmd": "pwd"})}}
        assert _get_tool_call_command(tc) == "pwd"

    def test_invalid_json_returns_none(self):
        tc = {"function": {"arguments": "not json"}}
        assert _get_tool_call_command(tc) is None

    def test_empty_args_returns_none(self):
        tc = {"function": {}}
        assert _get_tool_call_command(tc) is None


class TestSetToolCallCommand:
    """Tests for _set_tool_call_command."""

    def test_sets_command_in_args(self):
        tc = {"function": {"arguments": json.dumps({"command": "old"})}}
        _set_tool_call_command(tc, "ls -la")
        args = json.loads(tc["function"]["arguments"])
        assert args["command"] == "ls -la"

    def test_updates_cmd_if_present(self):
        tc = {"function": {"arguments": json.dumps({"command": "x", "cmd": "x"})}}
        _set_tool_call_command(tc, "new")
        args = json.loads(tc["function"]["arguments"])
        assert args["cmd"] == "new"


class TestInjectErrorMessage:
    """Tests for _inject_error_message."""

    def test_returns_dict_with_role_and_content(self):
        m = _inject_error_message("error text")
        assert m["role"] == "assistant"
        assert m["content"] == "error text"

    def test_custom_role(self):
        m = _inject_error_message("err", role="user")
        assert m["role"] == "user"


class TestResponseWithError:
    """Tests for _response_with_error."""

    def test_empty_choices_adds_one(self):
        body = {"choices": []}
        got = _response_with_error(body, "Blocked")
        assert len(got["choices"]) == 1
        assert got["choices"][0]["message"]["content"] == "Blocked"
        assert got["choices"][0]["finish_reason"] == "stop"

    def test_existing_choice_replaced(self):
        body = {"choices": [{"message": {"content": "original"}, "index": 0}]}
        got = _response_with_error(body, "Blocked")
        assert got["choices"][0]["message"]["content"] == "Blocked"


class TestGuardRequest:
    """Tests for guard_request."""

    def test_no_messages_under_limit(self):
        with patch("core.proxy.usage") as usage:
            usage.check_allow.return_value = (True, "")
            body = {"messages": []}
            modified, err = guard_request(body)
            assert err is None
            assert modified == body
            usage.add.assert_called_once()

    def test_over_limit_returns_error(self):
        with patch("core.proxy.usage") as usage:
            usage.check_allow.return_value = (False, "Token limit exceeded")
            body = {"messages": [{"role": "user", "content": "x"}]}
            modified, err = guard_request(body)
            assert modified is None
            assert err == "Token limit exceeded"
            usage.add.assert_not_called()


class TestGuardResponse:
    """Tests for guard_response."""

    def test_no_tool_calls_returns_body_unchanged(self):
        body = {"choices": [{"message": {"content": "hi"}}]}
        got, err = guard_response(body, require_approval=False)
        assert err is None
        assert got == body

    def test_dangerous_command_injected_error(self):
        body = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "1",
                                "function": {
                                    "name": "run_shell",
                                    "arguments": json.dumps({"command": "rm -rf /"}),
                                },
                            }
                        ]
                    }
                }
            ]
        }
        got, err = guard_response(body, require_approval=False)
        assert err is None
        # Response should have error message in first choice
        msg = got["choices"][0]["message"]
        assert "Blocked" in msg["content"] or "rm" in msg["content"].lower()

    def test_safe_read_only_command_passes(self):
        body = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "1",
                                "function": {
                                    "name": "run_shell",
                                    "arguments": json.dumps({"command": "ls -la"}),
                                },
                            }
                        ]
                    }
                }
            ]
        }
        with patch("core.proxy.rewrite_to_sandbox", side_effect=lambda c: c):
            got, err = guard_response(body, require_approval=False)
        assert err is None
        msg_content = got["choices"][0]["message"].get("content") or ""
        assert "Blocked" not in msg_content

    def test_non_shell_tool_ignored(self):
        body = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "1",
                                "function": {
                                    "name": "other_tool",
                                    "arguments": json.dumps({"x": "y"}),
                                },
                            }
                        ]
                    }
                }
            ]
        }
        got, err = guard_response(body, require_approval=False)
        assert err is None
        assert got == body
