"""
Dangerous command detection and blocking.
Blocks deletion, formatting, system config changes, and other sensitive operations.
"""
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Sensitive paths that must not be accessed (read or write)
SENSITIVE_PATH_PATTERNS: List[Tuple[str, str]] = [
    (r"/etc/", "system config /etc/"),
    (r"/boot/", "boot partition"),
    (r"\.ssh/", ".ssh directory"),
    (r"~/?\.ssh", "home .ssh"),
    (r"/\.ssh/", "root .ssh"),
    (r"System32", "Windows System32"),
    (r"system32", "Windows system32"),
    (r"/root/", "root home"),
    (r"/usr/bin/", "system binaries (write)"),
    (r"/usr/sbin/", "system sbin (write)"),
]

# Patterns that indicate dangerous operations (command or path/args)
DANGER_PATTERNS: List[Tuple[str, str]] = [
    # Deletion
    (r"\brm\s+(-rf?|-\s*rf?)\s", "bulk delete (rm -rf)"),
    (r"\brm\s+.*\/\s*$", "delete root or path"),
    (r"\bdd\s+", "raw disk write (dd)"),
    (r"\bmkfs\.", "format filesystem"),
    (r"\bformat\s+", "format"),
    # chmod 777 and similar (dangerous permissions)
    (r"\bchmod\s+777\b", "chmod 777"),
    (r"\bchmod\s+[0-7]{3,4}\s+.*\/", "chmod on system path"),
    (r"\bchown\s+.*\/", "chown on system path"),
    (r">\s*\/etc\/", "write to /etc"),
    (r">\s*\/boot\/", "write to /boot"),
    (r"\$\(.*\)\s*\|.*\s+sudo\s+", "piped to sudo"),
    (r"\bsudo\s+rm\s", "sudo rm"),
    (r"\bsudo\s+dd\s", "sudo dd"),
    (r"\bsudo\s+mkfs", "sudo mkfs"),
    (r"\bsudo\s+format\s", "sudo format"),
    (r"\bcurl\s+.*\s+\|\s*sh\s", "pipe curl to shell"),
    (r"\bwget\s+.*\s+\|\s*sh\s", "pipe wget to shell"),
    (r":\s*\(\s*\)\s*\{[^}]*\|\s*:[^}]*&\s*\}", "fork bomb pattern"),
    (r"\breboot\b", "reboot"),
    (r"\bhalt\b", "halt"),
    (r"\bpoweroff\b", "poweroff"),
    (r"\binit\s+[06]", "init 0/6 shutdown"),
    (r"\bshutdown\s+", "shutdown"),
    (r"\b/system/bin/rm\s", "Android/system rm"),
]

COMPILED: List[Tuple[re.Pattern, str]] = [
    (re.compile(p, re.IGNORECASE), label) for p, label in DANGER_PATTERNS
]
SENSITIVE_PATH_COMPILED: List[Tuple[re.Pattern, str]] = [
    (re.compile(p, re.IGNORECASE), label) for p, label in SENSITIVE_PATH_PATTERNS
]


@dataclass
class DangerResult:
    blocked: bool
    reason: Optional[str] = None
    matched_pattern: Optional[str] = None


def is_dangerous_command(text: str) -> DangerResult:
    """Check if text contains a dangerous command. Returns DangerResult."""
    if not text or not text.strip():
        return DangerResult(blocked=False)
    for pattern, label in COMPILED:
        if pattern.search(text):
            return DangerResult(blocked=True, reason=label, matched_pattern=pattern.pattern)
    for pattern, label in SENSITIVE_PATH_COMPILED:
        if pattern.search(text):
            return DangerResult(blocked=True, reason=f"sensitive path ({label})", matched_pattern=pattern.pattern)
    return DangerResult(blocked=False)


# Read-only commands (auto-pass, no approval). Substring match after stripping.
READ_ONLY_CMDS = frozenset({"ls", "cat", "pwd", "echo", "whoami", "date", "env", "printenv", "which", "type", "head", "tail", "grep", "find", "wc", "stat", "file", "id", "uname"})


def classify_operation(command: str) -> str:
    """
    Classify operation: "read_only" (auto pass) | "write" (needs approval).
    Call only after is_dangerous_command has already ruled out danger.
    """
    if not command or not command.strip():
        return "read_only"
    s = command.strip()
    # Write indicators: redirection to file, or write-like commands
    write_indicators = (">", ">>", "tee", "cp ", "mv ", "mkdir", "touch", "chmod", "chown", "sed -i", "curl -o", "wget -O")
    if any(w in s for w in write_indicators):
        return "write"
    # First token as command
    first = (s.split() or [""])[0]
    if first in READ_ONLY_CMDS:
        return "read_only"
    # Default: treat as write (needs approval)
    return "write"


def extract_shell_commands(content: str) -> List[str]:
    """
    Extract likely shell command strings from content (e.g. from code blocks or tool args).
    Returns list of candidate command strings to run through is_dangerous_command.
    """
    candidates: List[str] = []
    # Code blocks: ```bash ... ``` or ```sh ... ```
    for m in re.finditer(r"```(?:bash|sh|zsh|shell)\s*\n(.*?)```", content, re.DOTALL | re.IGNORECASE):
        candidates.append(m.group(1).strip())
    # Inline single-line commands often after $ or %
    for line in content.splitlines():
        s = line.strip()
        if re.match(r"^[$%]\s+", s):
            candidates.append(re.sub(r"^[$%]\s+", "", s))
    return candidates
