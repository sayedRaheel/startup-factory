# Changelog

## 1.0.0 - 2026-06-24

Initial release.

- Infer and print the schema skeleton (keys, types, array lengths, nesting) of a JSON document.
- Merge array elements / NDJSON records and flag optional keys with `?` and a present/total count.
- Union types for mixed-type arrays (e.g. `int|null|str`).
- Flags: `--ndjson`, `--depth N`, `--samples`, `--json`, `--version`.
- Reads from a file argument or stdin.
- Sensible exit codes (0 ok, 1 runtime error, 2 usage error).
- 16 unit tests.
