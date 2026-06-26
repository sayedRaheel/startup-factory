# Changelog

## 1.0.0 - 2026-06-26

Initial release.

- Detect and re-align GitHub-Flavored Markdown pipe tables.
- Honor per-column alignment markers (`:---`, `:---:`, `---:`).
- Read from stdin or files; write to stdout or in place with `-i`.
- `--check` mode exits 2 when any input is not already aligned (CI-friendly).
- Pad ragged rows, preserve escaped pipes (`\|`), and count wide CJK
  characters as width 2.
- Standard-library only; 16 unit tests.
