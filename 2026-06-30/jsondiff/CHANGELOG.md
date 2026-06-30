# Changelog

## 1.0.0 — 2026-06-30

Initial release.

- Semantic JSON comparison that ignores key order and formatting (pretty vs. minified).
- Reports added / removed / changed values with JSON paths (`root.a.b[0]`).
- `--ignore-array-order` to compare arrays as multisets.
- `--format text|json` output; colorized text on a TTY, `--no-color` to disable.
- `--quiet` mode plus `diff`-style exit codes (0 same, 1 differ, 2 error) for CI.
- Reads from files or stdin (`-`).
- 22 unit tests, no third-party dependencies.
