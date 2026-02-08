# Security

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

- Prefer **GitHub Security Advisories**: open the repo → Security → Advisories → "Report a vulnerability".
- Or contact the maintainers privately if you have a way to do so.

We will respond and, if you wish, credit you for the finding.

## Security-related behavior

- OpenClawGuard does not store shell command content long-term; approval state is in-memory (or lost on restart).
- Telegram/WeChat tokens and webhook URLs should be set via environment variables, not committed to the repo.
- The guard acts as a proxy; TLS should be handled by a reverse proxy (e.g. nginx) in production if you expose it.
