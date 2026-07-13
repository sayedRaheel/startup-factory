# Changelog

## 1.0.0 — 2026-07-13

- Initial release.
- Offline checking of relative file links and images in Markdown trees.
- Heading-anchor validation (GitHub slug rules: duplicates numbered, setext
  headings, `<a name=…>` HTML anchors).
- Skips fenced code blocks, inline code spans, and external URLs.
- `--format json`, `--root`, `--exclude`, `-q`, `--version`.
- Exit codes 0 / 1 / 2 for clean / broken / usage error.
- 15 stdlib unit tests plus a runnable `examples/docs` fixture.
