"""
HTTP reverse proxy to OpenClaw with guard logic.
- Inspects request/response for shell execution; blocks dangerous or requires approval.
- Rewrites paths to sandbox when enabled.
- Enforces token circuit breaker.
"""
import json
from typing import Any, Optional

import requests
from flask import Flask, request, Response, stream_with_context

import config as guard_config
from core.approval import approve, reject, request_approval, wait_approval
from core.danger import classify_operation, is_dangerous_command
from core.sandbox import rewrite_to_sandbox
from core.tokens import estimate_tokens, usage


def _target_base() -> str:
    return f"http://{guard_config.TARGET_HOST}:{guard_config.TARGET_PORT}"

# Tool names that imply shell execution (OpenAI-style tool_calls)
SHELL_TOOL_NAMES = ("run_terminal_cmd", "run_shell", "execute_command", "shell", "run_command", "exec")


def _count_message_tokens(obj: Any) -> int:
    """Estimate tokens in a chat message or tool call."""
    if isinstance(obj, str):
        return estimate_tokens(obj)
    if isinstance(obj, dict):
        return sum(_count_message_tokens(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(_count_message_tokens(x) for x in obj)
    return 0


def _extract_tool_calls_from_body(body: dict) -> list[dict]:
    """Extract tool_calls from request messages (assistant) or response choices."""
    out: list[dict] = []
    for msg in body.get("messages", []):
        for tc in msg.get("tool_calls") or []:
            out.append(tc)
    for choice in body.get("choices", []):
        msg = choice.get("message") or {}
        for tc in msg.get("tool_calls") or []:
            out.append(tc)
    return out


def _get_tool_call_command(tc: dict) -> Optional[str]:
    """Get the command string from a tool call (function.arguments as JSON)."""
    try:
        fn = tc.get("function") or {}
        args = fn.get("arguments")
        if isinstance(args, str):
            obj = json.loads(args)
        else:
            obj = args or {}
        return obj.get("command") or obj.get("cmd") or (obj.get("input") if isinstance(obj.get("input"), str) else None)
    except (json.JSONDecodeError, TypeError):
        return None


def _inject_error_message(content: str, role: str = "assistant") -> dict:
    """Build a minimal chat message dict for error injection."""
    return {"role": role, "content": content}


def guard_request(body: dict) -> tuple[Optional[dict], Optional[str]]:
    """
    Check request: token limit and optionally dangerous content in messages.
    Returns (modified_body, error_message). If error_message set, abort with it.
    """
    token_count = _count_message_tokens(body.get("messages", []))
    ok, msg = usage.check_allow(token_count)
    if not ok:
        return None, msg
    usage.add(token_count)
    return body, None


def _set_tool_call_command(tc: dict, new_command: str) -> None:
    """Mutate tool call function.arguments to use new_command."""
    fn = tc.get("function") or {}
    args = fn.get("arguments")
    if isinstance(args, str):
        try:
            obj = json.loads(args)
        except json.JSONDecodeError:
            obj = {}
    else:
        obj = dict(args or {})
    obj["command"] = new_command
    if "cmd" in obj:
        obj["cmd"] = new_command
    fn["arguments"] = json.dumps(obj)
    tc["function"] = fn


def guard_response(body: dict, require_approval: bool = True) -> tuple[dict, Optional[str]]:
    """
    Check response for shell tool calls: block dangerous, optionally require approval.
    Returns (modified_body, error_message). Injects sandbox-rewritten command into response when allowed.
    """
    tool_calls = _extract_tool_calls_from_body(body)
    for tc in tool_calls:
        fn = tc.get("function") or {}
        name = (fn.get("name") or "").lower()
        if not any(name == n for n in SHELL_TOOL_NAMES):
            continue
        command = _get_tool_call_command(tc)
        if not command:
            continue
        danger = is_dangerous_command(command)
        if danger.blocked:
            err = f"Blocked by ClawGuard: {danger.reason}"
            return _response_with_error(body, err), None
        command_rewritten = rewrite_to_sandbox(command)
        op = classify_operation(command_rewritten)
        # read_only: auto pass; write: require approval when notifier configured
        if op == "write" and require_approval and command_rewritten.strip():
            has_notifier = bool(guard_config.TELEGRAM_BOT_TOKEN and guard_config.TELEGRAM_CHAT_ID) or bool(guard_config.WECHAT_WEBHOOK_URL)
            if has_notifier:
                approval_id = request_approval(command_rewritten)
                if not wait_approval(approval_id):
                    return _response_with_error(body, "Shell execution not approved (timeout or rejected)."), None
            # else: no mobile notifier configured → allow
        if command_rewritten != command:
            _set_tool_call_command(tc, command_rewritten)
    return body, None


def _response_with_error(original: dict, error_content: str) -> dict:
    """Replace first choice message with error so client sees it."""
    choices = original.get("choices") or []
    if not choices:
        return {**original, "choices": [{"message": _inject_error_message(error_content), "index": 0, "finish_reason": "stop"}]}
    first = dict(choices[0])
    first["message"] = _inject_error_message(error_content)
    first["finish_reason"] = "stop"
    return {**original, "choices": [first] + choices[1:]}


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/clawguard/approve", methods=["GET", "POST"])
    def approval_approve():
        approval_id = request.args.get("id") or (request.get_json(silent=True) or {}).get("id")
        if not approval_id:
            return Response(json.dumps({"ok": False, "error": "missing id"}), status=400, mimetype="application/json")
        if approve(approval_id):
            return Response(json.dumps({"ok": True, "message": "approved"}), mimetype="application/json")
        return Response(json.dumps({"ok": False, "error": "not found or already decided"}), status=404, mimetype="application/json")

    @app.route("/clawguard/reject", methods=["GET", "POST"])
    def approval_reject():
        approval_id = request.args.get("id") or (request.get_json(silent=True) or {}).get("id")
        if not approval_id:
            return Response(json.dumps({"ok": False, "error": "missing id"}), status=400, mimetype="application/json")
        if reject(approval_id):
            return Response(json.dumps({"ok": True, "message": "rejected"}), mimetype="application/json")
        return Response(json.dumps({"ok": False, "error": "not found or already decided"}), status=404, mimetype="application/json")

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    def proxy(path: str):
        if request.method == "OPTIONS":
            return Response(status=204)
        url = f"{_target_base()}/{path}"
        if request.query_string:
            url += "?" + request.query_string.decode()
        headers = {k: v for k, v in request.headers if k.lower() != "host"}
        # Request body
        body: Optional[dict] = None
        if request.is_json:
            try:
                body = request.get_json(force=True, silent=True) or {}
            except Exception:
                body = {}
        if body:
            modified, err = guard_request(body)
            if err:
                return Response(json.dumps({"error": {"message": err}}), status=429, mimetype="application/json")
        # Stream or not
        stream = bool(body and body.get("stream"))
        if stream:
            # For streaming we don't easily intercept tool_calls mid-stream; forward and optionally post-process.
            # Simplified: forward stream to target and back (no approval in stream path here).
            def gen():
                with requests.request(
                    request.method,
                    url,
                    headers=headers,
                    data=request.get_data(),
                    stream=True,
                    timeout=60,
                ) as r:
                    for chunk in r.iter_content(chunk_size=None):
                        if chunk:
                            yield chunk

            return Response(stream_with_context(gen()), mimetype="application/json")
        # Non-stream
        try:
            resp = requests.request(
                request.method,
                url,
                headers=headers,
                data=request.get_data() if not body else None,
                json=modified if body else None,
                timeout=120,
            )
        except requests.exceptions.ConnectionError:
            return Response(
                json.dumps({"error": {"message": "OpenClaw backend unreachable. Is it running on the target port?"}}),
                status=502,
                mimetype="application/json",
            )
        if resp.status_code != 200:
            return Response(resp.content, status=resp.status_code, mimetype=resp.headers.get("Content-Type", "application/json"))
        try:
            data = resp.json()
        except Exception:
            return Response(resp.content, status=resp.status_code, mimetype=resp.headers.get("Content-Type", "application/json"))
        # Guard response
        guarded, err_msg = guard_response(data)
        if err_msg:
            return Response(json.dumps({"error": {"message": err_msg}}), status=403, mimetype="application/json")
        return Response(json.dumps(guarded), mimetype="application/json")

    return app


def run_proxy(port: Optional[int] = None) -> None:
    port = port or guard_config.GUARD_PORT
    create_app().run(host="0.0.0.0", port=port, threaded=True)
