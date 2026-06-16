# Changelog

## 1.0.0 — 2026-06-16

Initial release of `cronwise`, an offline cron expression explainer and
next-run calculator.

- Parse standard 5-field cron expressions: `*`, `a`, `a-b`, `a-b/n`, `*/n`,
  comma lists, and named months (`JAN`–`DEC`) / weekdays (`SUN`–`SAT`).
- Support `0`/`7` Sunday alias and the macros `@yearly`, `@annually`,
  `@monthly`, `@weekly`, `@daily`, `@midnight`, `@hourly`.
- Plain-English description of any expression.
- Next-run computation with correct OR-semantics when both day-of-month and
  day-of-week are restricted.
- `--from`, `-n/--next`, and `-q/--quiet` flags; distinct exit codes (0/1/2).
- Standard-library-only; no third-party dependencies.
- 12-case unittest suite (`test_cronwise.py`), all passing.
