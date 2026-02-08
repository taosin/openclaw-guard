<p align="center">
  <img src="https://img.shields.io/github/stars/taosin/openclaw-guard?style=social" alt="GitHub stars">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/python-3.9+-green.svg" alt="Python">
  <img src="https://img.shields.io/badge/OpenClaw-compatible-orange" alt="OpenClaw">
</p>

# 🛡️ OpenClawGuard

> **One sentence:** Give your local AI assistant a security layer—block dangerous shell commands, require human approval for writes, and cap token usage so one prompt can't blow your bill.

**OpenClaw has shell access by default.** A malicious page or email could trick the AI into running `rm -rf /`. OpenClawGuard sits in front of OpenClaw as a proxy: it filters dangerous commands, sends write operations to your phone for approval (Telegram/WeChat), redirects file access to a sandbox, and trips a circuit breaker when token usage gets too high.

[English](#quick-start) | [中文说明](docs/USER_GUIDE.md)

---

## ✨ Why OpenClawGuard?

| Without Guard                        | With OpenClawGuard                                                    |
| ------------------------------------ | --------------------------------------------------------------------- |
| AI can run `rm -rf /` if tricked     | Dangerous commands are **blocked** by pattern + sensitive-path checks |
| Every shell run executes immediately | **Write** operations need your **Approve** on your phone              |
| File ops can touch `/etc`, `~/.ssh`  | Paths are **rewritten** to `/workspace` (or your sandbox)             |
| Runaway loops can burn tokens        | **Token circuit breaker** stops requests when limit is hit            |

---

## 🚀 Quick Start (3 steps)

```bash
# 1. Clone & install
git clone https://github.com/taosin/openclaw-guard.git
cd openclaw-guard
pip install -r requirements.txt

# 2. Start OpenClaw on 8080 (if not already), then start the guard
python clawguard.py --target-port 8080

# 3. Point your client (e.g. Cursor) to http://localhost:8081 instead of 8080
```

Guard listens on **8081** and forwards to OpenClaw on **8080**. All traffic goes through the guard.

---

## 📋 Core Features

- **🛑 Danger blocking** — Blocks `rm -rf`, `mkfs`, `dd`, `chmod 777`, access to `/etc`, `~/.ssh`, `System32`, etc.
- **📱 Human-in-the-loop** — Write operations trigger Telegram/WeChat; you Approve or Deny with one tap (or HTTP link).
- **📂 Sandbox** — File operations are redirected to `/workspace` (configurable) so the rest of the filesystem stays safe.
- **🔌 Token circuit breaker** — Stops requests when token usage in a time window exceeds a limit (e.g. daily cap).

---

## 📖 Docs & Flowcharts

- **[User guide (with flowcharts)](docs/USER_GUIDE.md)** — Architecture, request flow, approval flow, config, Docker, FAQ.
- **[Requirements compliance](docs/REQUIREMENTS_COMPLIANCE.md)** — Mapping to ClawGuard V1.0 functional requirements.
- **[CHANGELOG](CHANGELOG.md)** — Release history (auto-updated on merge to `main` via [Conventional Commits](https://www.conventionalcommits.org/)).

---

## ⚙️ Configuration (highlights)

| Variable                                                      | Description                                      |
| ------------------------------------------------------------- | ------------------------------------------------ |
| `CLAWGUARD_TARGET_PORT`                                       | OpenClaw port (default `8080`)                   |
| `CLAWGUARD_PORT`                                              | Guard port (default `8081`)                      |
| `CLAWGUARD_SANDBOX`                                           | Sandbox dir (default `/workspace`)               |
| `CLAWGUARD_TOKEN_LIMIT`                                       | Token cap (default `100000`)                     |
| `CLAWGUARD_TOKEN_WINDOW_SEC`                                  | Window in seconds; use `86400` for daily         |
| `CLAWGUARD_PUBLIC_URL`                                        | Base URL for Approve/Deny links in notifications |
| `CLAWGUARD_TELEGRAM_BOT_TOKEN` / `CLAWGUARD_TELEGRAM_CHAT_ID` | Telegram approval                                |
| `CLAWGUARD_WECHAT_WEBHOOK_URL`                                | WeChat approval                                  |

Full list and examples: [User guide → Configuration](docs/USER_GUIDE.md#五配置说明).

---

## 🔗 Approval API

When a write needs approval, you get a notification with two links (if `CLAWGUARD_PUBLIC_URL` is set). You can also call:

- **Approve:** `GET` or `POST` `/clawguard/approve?id=<approval_id>`
- **Reject:** `GET` or `POST` `/clawguard/reject?id=<approval_id>`

Example: `curl http://localhost:8081/clawguard/approve?id=abc-123`

---

## 🐳 Docker

```bash
cp docker-compose.example.yml docker-compose.yml
# Edit env (e.g. CLAWGUARD_PUBLIC_URL, Telegram)
docker compose up -d
```

OpenClaw can run on the host; set `CLAWGUARD_TARGET_HOST=host.docker.internal`. See [User guide → Docker](docs/USER_GUIDE.md#六docker-一键部署).

---

## 🧪 Running tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Optional: `pytest tests/ --cov=core --cov=config --cov-report=term-missing` for coverage.

---

## 🤝 Contributing

We welcome issues and PRs. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

[MIT](LICENSE).
