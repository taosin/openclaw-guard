"""
Mobile one-tap approval for shell execution.
Sends Telegram or WeChat notification; command proceeds only after approval or timeout.
"""
import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable, Optional

import requests

from config import (
    APPROVAL_TIMEOUT_SEC,
    GUARD_PUBLIC_URL,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    WECHAT_WEBHOOK_URL,
)


@dataclass
class PendingApproval:
    id: str
    command: str
    created_at: float
    approved: Optional[bool] = None
    done: bool = False


_store: dict[str, PendingApproval] = {}
_store_lock = Lock()


def request_approval(command: str, notify_callback: Optional[Callable[[str, str], None]] = None) -> str:
    """
    Register a pending approval and optionally send notification.
    Returns approval_id. Caller should wait via wait_approval(approval_id).
    """
    approval_id = str(uuid.uuid4())
    with _store_lock:
        _store[approval_id] = PendingApproval(
            id=approval_id,
            command=command,
            created_at=time.time(),
        )
    if notify_callback:
        try:
            notify_callback(approval_id, command)
        except Exception:
            pass
    else:
        _send_notification(approval_id, command)
    return approval_id


def _send_notification(approval_id: str, command: str) -> None:
    """Send Telegram or WeChat notification with one-click Approve/Deny links."""
    preview = (command[:200] + "…") if len(command) > 200 else command
    approve_url = f"{GUARD_PUBLIC_URL}/clawguard/approve?id={approval_id}"
    reject_url = f"{GUARD_PUBLIC_URL}/clawguard/reject?id={approval_id}"
    text = (
        f"🛡 OpenClawGuard: Approve shell command?\n\n{preview}\n\n"
        f"✅ Approve: {approve_url}\n"
        f"❌ Deny: {reject_url}"
    )
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
                timeout=10,
            )
        except Exception:
            pass
    if WECHAT_WEBHOOK_URL:
        try:
            requests.post(
                WECHAT_WEBHOOK_URL,
                json={
                    "msgtype": "text",
                    "text": {"content": text},
                },
                timeout=10,
            )
        except Exception:
            pass


def approve(approval_id: str) -> bool:
    """Mark approval as granted. Returns True if found and not already decided."""
    with _store_lock:
        p = _store.get(approval_id)
        if not p or p.done:
            return False
        p.approved = True
        p.done = True
        return True


def reject(approval_id: str) -> bool:
    """Mark approval as rejected."""
    with _store_lock:
        p = _store.get(approval_id)
        if not p or p.done:
            return False
        p.approved = False
        p.done = True
        return True


def wait_approval(approval_id: str, timeout_sec: Optional[float] = None) -> bool:
    """Block until approval is decided or timeout. Returns True if approved."""
    timeout_sec = timeout_sec or APPROVAL_TIMEOUT_SEC
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        with _store_lock:
            p = _store.get(approval_id)
            if not p:
                return False
            if p.done:
                return p.approved is True
        time.sleep(0.2)
    with _store_lock:
        p = _store.get(approval_id)
        if p and not p.done:
            p.approved = False
            p.done = True
    return False


def get_pending(approval_id: str) -> Optional[PendingApproval]:
    with _store_lock:
        return _store.get(approval_id)
