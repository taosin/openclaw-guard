"""Unit tests for clawguard entrypoint."""
import sys
from unittest.mock import patch

import pytest


class TestMain:
    """Tests for main() and CLI."""

    def test_help_exits_zero(self):
        with patch.object(sys, "argv", ["clawguard", "--help"]):
            with pytest.raises(SystemExit) as exc:
                import clawguard

                clawguard.main()
            assert exc.value.code == 0

    def test_parse_args_defaults(self):
        with patch("clawguard.run_proxy") as run_proxy, patch("clawguard.ensure_sandbox_exists"):
            with patch.object(sys, "argv", ["clawguard"]):
                import clawguard

                clawguard.main()
            run_proxy.assert_called_once()
            assert run_proxy.call_args.kwargs.get("port") is not None

    def test_parse_args_port_override(self):
        with patch("clawguard.run_proxy") as run_proxy, patch("clawguard.ensure_sandbox_exists"):
            with patch.object(sys, "argv", ["clawguard", "--port", "9999", "--target-port", "8888"]):
                import clawguard

                clawguard.main()
            run_proxy.assert_called_once_with(port=9999)
        import config as cfg
        assert cfg.GUARD_PORT == 9999
        assert cfg.TARGET_PORT == 8888
        # Restore defaults so other tests aren't affected
        import importlib
        importlib.reload(cfg)

    def test_no_sandbox_flag(self):
        with patch("clawguard.run_proxy"), patch("clawguard.ensure_sandbox_exists"):
            with patch.object(sys, "argv", ["clawguard", "--no-sandbox"]):
                import clawguard

                clawguard.main()
        import config as cfg
        assert cfg.SANDBOX_ENABLED is False
        cfg.SANDBOX_ENABLED = True  # Restore for other code
