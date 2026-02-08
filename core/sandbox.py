"""
Sandbox path redirection.
Rewrites file paths in commands so that operations target /sandbox instead of root.
"""
import re
from pathlib import Path
from typing import Optional

from config import SANDBOX_DIR, SANDBOX_ENABLED


def rewrite_to_sandbox(command: str, sandbox_root: Optional[Path] = None) -> str:
    """
    Rewrite paths in a shell command to under sandbox_root (default SANDBOX_DIR).
    Only applied when SANDBOX_ENABLED is True; otherwise returns command unchanged.
    """
    if not SANDBOX_ENABLED:
        return command
    root = (sandbox_root or SANDBOX_DIR).as_posix()
    if not root.endswith("/"):
        root += "/"

    out = command
    # Paths that start with / but not /sandbox (or current sandbox root)
    # Replace leading / with sandbox root (e.g. /etc -> /sandbox/etc)
    def repl(m: re.Match) -> str:
        path = m.group(2)  # the path (group 1 = leading space, 2 = path, 3 = trailing)
        if path.startswith(root) or path == "/":
            return m.group(0)
        if path.startswith("/"):
            return m.group(1) + (root.rstrip("/") + path) + m.group(3)
        return m.group(0)

    # Common: > /path, >> /path, < /path, cmd /path, rm /path, etc.
    out = re.sub(r"(\s)(\/[a-zA-Z0-9_/.][a-zA-Z0-9_/.-]*)(\s|$)", repl, out)
    # Quoted paths: "/path" or '/path'
    out = re.sub(r"([\"'])(\/[a-zA-Z0-9_/.][a-zA-Z0-9_/.-]*)\1", lambda m: m.group(1) + root.rstrip("/") + m.group(2) + m.group(1), out)
    return out


def ensure_sandbox_exists(sandbox_root: Optional[Path] = None) -> None:
    """Create sandbox directory if it does not exist."""
    if not SANDBOX_ENABLED:
        return
    root = sandbox_root or SANDBOX_DIR
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
