"""Unit tests for config (env loading)."""
import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestConfig:
    """Basic config tests (import-time env)."""

    def test_import_succeeds(self):
        import config
        assert hasattr(config, "TARGET_PORT")
        assert hasattr(config, "GUARD_PORT")
        assert hasattr(config, "SANDBOX_DIR")
        assert hasattr(config, "TOKEN_LIMIT")

    def test_sandbox_dir_is_path(self):
        import config
        assert isinstance(config.SANDBOX_DIR, Path)

    def test_ports_are_int(self):
        import config
        assert isinstance(config.TARGET_PORT, int)
        assert isinstance(config.GUARD_PORT, int)
        assert isinstance(config.TOKEN_LIMIT, int)
