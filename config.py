"""
OpenClawGuard configuration.
Override via environment variables: CLAWGUARD_* or .env (if loaded).
"""
import os
from pathlib import Path

# Proxy
TARGET_HOST = os.environ.get("CLAWGUARD_TARGET_HOST", "127.0.0.1")
TARGET_PORT = int(os.environ.get("CLAWGUARD_TARGET_PORT", "8080"))
GUARD_PORT = int(os.environ.get("CLAWGUARD_PORT", "8081"))

# Sandbox (only allow AI to read/write under this dir; default /workspace per requirement)
SANDBOX_DIR = Path(os.environ.get("CLAWGUARD_SANDBOX", "/workspace")).resolve()
SANDBOX_ENABLED = os.environ.get("CLAWGUARD_SANDBOX_ENABLED", "true").lower() in ("1", "true", "yes")

# Token circuit breaker (rough chars/4 as token estimate). Set TOKEN_WINDOW_SEC=86400 for daily limit.
TOKEN_LIMIT = int(os.environ.get("CLAWGUARD_TOKEN_LIMIT", "100000"))
TOKEN_WINDOW_RESET_SEC = int(os.environ.get("CLAWGUARD_TOKEN_WINDOW_SEC", "3600"))  # 86400 = daily

# Mobile approval
TELEGRAM_BOT_TOKEN = os.environ.get("CLAWGUARD_TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("CLAWGUARD_TELEGRAM_CHAT_ID", "")
WECHAT_WEBHOOK_URL = os.environ.get("CLAWGUARD_WECHAT_WEBHOOK_URL", "")
APPROVAL_TIMEOUT_SEC = int(os.environ.get("CLAWGUARD_APPROVAL_TIMEOUT", "300"))
# Base URL for one-click approve/deny links in notifications (e.g. https://guard.example.com or http://localhost:8081)
GUARD_PUBLIC_URL = os.environ.get("CLAWGUARD_PUBLIC_URL", "http://localhost:8081").rstrip("/")

# Execution time limit (placeholder; actual enforcement depends on executor)
MAX_EXECUTION_SEC = int(os.environ.get("CLAWGUARD_MAX_EXECUTION_SEC", "0"))  # 0 = no limit
