"""Unit tests for core.tokens."""
import time
from unittest.mock import patch

import pytest

from core.tokens import TokenUsage, estimate_tokens


class TestEstimateTokens:
    """Tests for estimate_tokens."""

    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_rough_chars_per_token(self):
        # ~4 chars per token
        assert estimate_tokens("a" * 4) == 1
        assert estimate_tokens("a" * 8) == 2
        assert estimate_tokens("hello world") >= 2  # 11 chars -> at least 2

    def test_min_one_for_non_empty(self):
        assert estimate_tokens("x") >= 1
        assert estimate_tokens("ab") >= 1


class TestTokenUsage:
    """Tests for TokenUsage (circuit breaker)."""

    def test_check_allow_initially_allows(self):
        with patch("core.tokens.TOKEN_LIMIT", 1000), patch("core.tokens.TOKEN_WINDOW_RESET_SEC", 3600):
            u = TokenUsage()
            ok, msg = u.check_allow(100)
            assert ok is True
            assert msg == ""

    def test_add_and_check_allow_under_limit(self):
        with patch("core.tokens.TOKEN_LIMIT", 1000), patch("core.tokens.TOKEN_WINDOW_RESET_SEC", 3600):
            u = TokenUsage()
            u.add(100)
            u.add(200)
            ok, msg = u.check_allow(500)
            assert ok is True

    def test_exceeding_limit_locks(self):
        with patch("core.tokens.TOKEN_LIMIT", 100), patch("core.tokens.TOKEN_WINDOW_RESET_SEC", 3600):
            u = TokenUsage()
            u.add(100)
            assert u.locked is True
            ok, msg = u.check_allow(0)
            assert ok is False
            assert "circuit" in msg.lower() or "limit" in msg.lower()

    def test_check_allow_rejects_when_additional_would_exceed(self):
        with patch("core.tokens.TOKEN_LIMIT", 100), patch("core.tokens.TOKEN_WINDOW_RESET_SEC", 3600):
            u = TokenUsage()
            u.add(80)
            ok, msg = u.check_allow(30)
            assert ok is False
            assert "limit" in msg.lower() or "exceed" in msg.lower()

    def test_reset_after_window(self):
        with patch("core.tokens.TOKEN_LIMIT", 100), patch("core.tokens.TOKEN_WINDOW_RESET_SEC", 0.1):
            u = TokenUsage()
            u.add(100)
            assert u.locked is True
            time.sleep(0.2)
            u._maybe_reset()
            assert u.locked is False
            assert u.total == 0
            ok, _ = u.check_allow(50)
            assert ok is True
