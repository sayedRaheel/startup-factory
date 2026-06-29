# Changelog

## 1.0.0 - 2026-06-28

Initial release.

- Walk a file or directory and collect TODO/FIXME-style annotation comments.
- Default tags: FIXME, BUG, XXX, HACK, TODO, OPTIMIZE, NOTE (configurable via `--tags`).
- Comment-leader-aware matching to avoid false positives inside strings/identifiers.
- Optional `(author)` parsing.
- Output formats: text (colorized), markdown, json, csv.
- Auto-skips VCS/build/dependency directories and binary files.
- `--exclude` globs, `--output` to file, `--no-color`, `--no-summary`, `--follow-symlinks`.
- `--fail-on TAGS` for CI gating (exit code 1 when matched).
- 15 unit tests; bundled `sample_project/` and `demo.sh`.
