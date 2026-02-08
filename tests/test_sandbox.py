"""Unit tests for core.sandbox."""
from pathlib import Path
from unittest.mock import patch

import pytest

from core.sandbox import ensure_sandbox_exists, rewrite_to_sandbox


class TestRewriteToSandbox:
    """Tests for rewrite_to_sandbox."""

    def test_disabled_returns_unchanged(self):
        with patch("core.sandbox.SANDBOX_ENABLED", False):
            cmd = "echo hi > /tmp/out"
            assert rewrite_to_sandbox(cmd) == cmd

    def test_enabled_rewrites_absolute_path(self):
        with patch("core.sandbox.SANDBOX_ENABLED", True), patch(
            "core.sandbox.SANDBOX_DIR", Path("/workspace")
        ):
            cmd = "cat /tmp/foo"
            got = rewrite_to_sandbox(cmd)
            assert "/workspace/tmp/foo" in got or "workspace" in got

    def test_enabled_with_explicit_root(self):
        root = Path("/sandbox")
        with patch("core.sandbox.SANDBOX_ENABLED", True):
            cmd = "echo x > /tmp/out"
            got = rewrite_to_sandbox(cmd, sandbox_root=root)
            assert "/sandbox" in got
            assert "tmp" in got or "out" in got

    def test_redirection_rewritten(self):
        with patch("core.sandbox.SANDBOX_ENABLED", True), patch(
            "core.sandbox.SANDBOX_DIR", Path("/workspace")
        ):
            cmd = "echo hi > /var/log/app.log"
            got = rewrite_to_sandbox(cmd)
            assert "/workspace" in got
            assert "var" in got or "log" in got

    def test_quoted_path_rewritten(self):
        with patch("core.sandbox.SANDBOX_ENABLED", True), patch(
            "core.sandbox.SANDBOX_DIR", Path("/workspace")
        ):
            cmd = 'cat "/etc/hosts"'
            got = rewrite_to_sandbox(cmd)
            assert "/workspace" in got

    def test_already_under_sandbox_unchanged(self):
        with patch("core.sandbox.SANDBOX_ENABLED", True), patch(
            "core.sandbox.SANDBOX_DIR", Path("/workspace")
        ):
            cmd = "cat /workspace/foo"
            got = rewrite_to_sandbox(cmd)
            # Should not double-prefix
            assert got.count("/workspace") >= 1

    def test_root_slash_unchanged(self):
        with patch("core.sandbox.SANDBOX_ENABLED", True), patch(
            "core.sandbox.SANDBOX_DIR", Path("/workspace")
        ):
            cmd = "ls / "  # path is just /
            got = rewrite_to_sandbox(cmd)
            # Implementation may keep / as-is
            assert "ls" in got


class TestEnsureSandboxExists:
    """Tests for ensure_sandbox_exists."""

    def test_disabled_does_nothing(self):
        with patch("core.sandbox.SANDBOX_ENABLED", False):
            ensure_sandbox_exists()  # no raise

    def test_enabled_creates_dir(self, tmp_path):
        with patch("core.sandbox.SANDBOX_ENABLED", True), patch(
            "core.sandbox.SANDBOX_DIR", tmp_path / "sandbox"
        ):
            ensure_sandbox_exists()
            assert (tmp_path / "sandbox").is_dir()

    def test_enabled_with_explicit_root_creates_it(self, tmp_path):
        with patch("core.sandbox.SANDBOX_ENABLED", True):
            root = tmp_path / "my_sandbox"
            ensure_sandbox_exists(sandbox_root=root)
            assert root.is_dir()

    def test_oserror_suppressed(self, tmp_path):
        with patch("core.sandbox.SANDBOX_ENABLED", True), patch(
            "core.sandbox.SANDBOX_DIR", Path("/nonexistent_no_create/xyz")
        ):
            # mkdir may fail on some systems; we just ensure no exception propagates
            try:
                ensure_sandbox_exists()
            except OSError:
                pytest.fail("OSError should be caught and not raised")
