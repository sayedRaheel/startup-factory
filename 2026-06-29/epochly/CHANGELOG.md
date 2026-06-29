# Changelog

## 1.0.0 — 2026-06-29

Initial release.

- Convert numeric epochs to dates with automatic seconds/millis/micros/nanos
  detection (override with `--unit`).
- Parse ISO-8601 and common human date strings back into epochs.
- `now` command and `diff A B` duration command.
- Relative phrasing ("2 years ago", "in 3 hours").
- `--tz` named-timezone output (graceful fallback when `zoneinfo` is absent),
  `--format` custom strftime, and `--json` machine-readable output.
- 22 unit tests covering detection, conversion, parsing, and the CLI.
