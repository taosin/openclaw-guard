"""Unit tests for core.approval."""
import time
from unittest.mock import patch

import pytest

from core.approval import (
    PendingApproval,
    approve,
    get_pending,
    reject,
    request_approval,
    wait_approval,
)


class TestRequestApproval:
    """Tests for request_approval."""

    def test_returns_approval_id(self):
        with patch("core.approval._send_notification"):
            aid = request_approval("ls -la")
            assert aid
            assert len(aid) == 36  # uuid4 hex + dashes

    def test_stores_pending(self):
        with patch("core.approval._send_notification"):
            aid = request_approval("echo hi")
            p = get_pending(aid)
            assert p is not None
            assert p.command == "echo hi"
            assert p.done is False

    def test_notify_callback_called(self):
        cb_called = []

        def cb(aid: str, cmd: str):
            cb_called.append((aid, cmd))

        with patch("core.approval._send_notification"):
            aid = request_approval("pwd", notify_callback=cb)
            assert len(cb_called) == 1
            assert cb_called[0][0] == aid
            assert cb_called[0][1] == "pwd"


class TestApproveReject:
    """Tests for approve and reject."""

    def test_approve_marks_done_and_approved(self):
        with patch("core.approval._send_notification"):
            aid = request_approval("ls")
        assert approve(aid) is True
        p = get_pending(aid)
        assert p is not None
        assert p.approved is True
        assert p.done is True
        # Second approve returns False (already decided)
        assert approve(aid) is False

    def test_reject_marks_done_and_not_approved(self):
        with patch("core.approval._send_notification"):
            aid = request_approval("rm -rf /")
        assert reject(aid) is True
        p = get_pending(aid)
        assert p is not None
        assert p.approved is False
        assert p.done is True
        assert reject(aid) is False

    def test_approve_unknown_id_returns_false(self):
        assert approve("nonexistent-id-12345") is False

    def test_reject_unknown_id_returns_false(self):
        assert reject("nonexistent-id-12345") is False


class TestWaitApproval:
    """Tests for wait_approval."""

    def test_approved_returns_true(self):
        with patch("core.approval._send_notification"):
            aid = request_approval("ls")
        approve(aid)
        assert wait_approval(aid, timeout_sec=1.0) is True

    def test_rejected_returns_false(self):
        with patch("core.approval._send_notification"):
            aid = request_approval("ls")
        reject(aid)
        assert wait_approval(aid, timeout_sec=1.0) is False

    def test_unknown_id_returns_false(self):
        assert wait_approval("nonexistent-id", timeout_sec=0.1) is False

    def test_timeout_returns_false(self):
        with patch("core.approval._send_notification"):
            aid = request_approval("ls")
            # Do not approve
        assert wait_approval(aid, timeout_sec=0.3) is False


class TestGetPending:
    """Tests for get_pending."""

    def test_returns_none_for_unknown(self):
        assert get_pending("no-such-id") is None

    def test_returns_pending_approval(self):
        with patch("core.approval._send_notification"):
            aid = request_approval("cat foo")
        p = get_pending(aid)
        assert isinstance(p, PendingApproval)
        assert p.id == aid
        assert p.command == "cat foo"
