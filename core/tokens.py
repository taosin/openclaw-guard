"""
Token circuit breaker.
Estimates token usage and blocks when limit is exceeded within a time window.
"""
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional

from config import TOKEN_LIMIT, TOKEN_WINDOW_RESET_SEC


def estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 chars per token for English/code."""
    if not text:
        return 0
    return max(1, len(text) // 4)


@dataclass
class TokenUsage:
    total: int = 0
    window_start: float = field(default_factory=time.time)
    locked: bool = False

    _lock: Lock = field(default_factory=Lock)

    def add(self, count: int) -> None:
        with self._lock:
            self._maybe_reset()
            self.total += count
            if self.total >= TOKEN_LIMIT:
                self.locked = True

    def _maybe_reset(self) -> None:
        if time.time() - self.window_start >= TOKEN_WINDOW_RESET_SEC:
            self.total = 0
            self.window_start = time.time()
            self.locked = False

    def check_allow(self, additional: int = 0) -> tuple[bool, str]:
        """Returns (allowed, message)."""
        with self._lock:
            self._maybe_reset()
            if self.locked:
                return False, f"Token circuit breaker tripped (limit {TOKEN_LIMIT})"
            if self.total + additional > TOKEN_LIMIT:
                return False, f"Token limit would be exceeded ({self.total + additional} > {TOKEN_LIMIT})"
            return True, ""


# Global usage for the proxy
usage = TokenUsage()
