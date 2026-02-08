# Contributing to OpenClawGuard

Thank you for considering contributing. Every issue and PR helps.

## How to contribute

- **Bug reports & feature ideas** — Open an [Issue](https://github.com/taosin/openclaw-guard/issues). Use the templates when possible.
- **Code & docs** — Open a Pull Request. Keep changes focused and add a short description in the PR.

## Commit messages (for automatic releases)

We use [Conventional Commits](https://www.conventionalcommits.org/) so that merging to `main` can auto-generate the changelog and create a GitHub Release. **Use English** for commit and PR titles.

- `feat: add something` — new feature (minor version bump)
- `fix: resolve something` — bug fix (patch bump)
- `docs: update readme` — documentation only (no release bump by default)
- `chore: ...`, `refactor: ...`, `test: ...`, `style: ...` — no version bump unless configured
- Add `BREAKING CHANGE:` in the footer (or use `feat!:` / `fix!:`) for a major version bump

Examples:

```
feat: add WeChat webhook for approval notifications
fix: prevent proxy from hanging on empty request body
docs: add Docker section to user guide
```

## Development setup

```bash
git clone https://github.com/taosin/openclaw-guard.git
cd openclaw-guard
pip install -r requirements.txt
# Run guard (optional: point to a local OpenClaw)
python clawguard.py --target-port 8080
```

## Code style

- Python: follow PEP 8; no strict formatter required, but keep style consistent.
- Prefer small, focused PRs with a clear title.

## Reporting security issues

Please do **not** open public issues for security vulnerabilities. Describe the issue in a private way (e.g. GitHub Security Advisories or email if you have a contact). We will respond and credit you if you wish.

## Questions

Open a [Discussion](https://github.com/taosin/openclaw-guard/discussions) or an Issue with the "question" label.

Thanks again.
