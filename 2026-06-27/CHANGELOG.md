# Changelog

## 1.0.0 - 2026-06-27

Initial release.

- Tokenise and parse curl commands (quotes, line continuations,
  `--flag=value`, unknown-flag tolerance).
- Code generators for Python (`requests`), JavaScript (`fetch`), and HTTPie.
- JSON body detection -> idiomatic `json=` / `field:=value` output.
- Basic-auth (`-u`) handling, including base64 Authorization header for fetch.
- `-G/--get` moves `-d` data into the URL query string, matching curl.
- Reads the command from arguments or stdin.
- 20 unit tests; standard library only, no third-party dependencies.
