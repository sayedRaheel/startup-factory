# Changelog

## 1.0.0 — 2026-07-07
- Initial release: static serving with CORS headers (configurable origin) and
  OPTIONS preflight handling.
- No-cache responses by default; `--cache` to opt out.
- `--spa` fallback for extension-less client routes.
- `--proxy /prefix=URL` same-origin API proxy (repeatable), path preserved,
  502 on unreachable upstream.
- Exit codes: 2 (bad directory), 3 (port in use).
- 12-test suite using real ephemeral-port servers; demo script.
