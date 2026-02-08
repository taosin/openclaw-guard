#!/usr/bin/env python3
"""
OpenClawGuard — Arm OpenClaw with armor.
Proxy that sits in front of OpenClaw to block dangerous commands,
require mobile approval for shell execution, redirect to sandbox, and enforce token limits.
"""
import argparse
import sys

from config import GUARD_PORT, SANDBOX_DIR, TARGET_PORT
from core.sandbox import ensure_sandbox_exists
from core.proxy import create_app, run_proxy


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OpenClawGuard: protect your local OpenClaw from dangerous shell use."
    )
    parser.add_argument(
        "--target-port",
        type=int,
        default=TARGET_PORT,
        help=f"OpenClaw backend port (default: {TARGET_PORT})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=GUARD_PORT,
        help=f"Guard proxy listen port (default: {GUARD_PORT})",
    )
    parser.add_argument(
        "--no-sandbox",
        action="store_true",
        help="Disable sandbox path redirection",
    )
    args = parser.parse_args()

    # Override config from CLI
    import config
    config.TARGET_PORT = args.target_port
    config.GUARD_PORT = args.port
    if args.no_sandbox:
        config.SANDBOX_ENABLED = False

    ensure_sandbox_exists()
    print(f"OpenClawGuard listening on port {args.port}, forwarding to target port {args.target_port}.")
    print(f"Sandbox: {'disabled' if args.no_sandbox else SANDBOX_DIR}")
    run_proxy(port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
