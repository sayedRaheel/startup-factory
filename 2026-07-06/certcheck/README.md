# certcheck

Check TLS certificate expiry for one or more hosts from the command line — without the unmemorable `openssl` double-pipe incantation, and with exit codes you can put in cron or CI.

**The problem:** Expired TLS certificates still take sites down all the time, and the standard way to check one from a shell is `echo | openssl s_client -servername HOST -connect HOST:443 2>/dev/null | openssl x509 -noout -dates` — a one-liner almost nobody remembers, that checks one host at a time, and that gives you raw date strings instead of "you have 12 days left."

**Sources:** Reddit blocks automated fetching from this build environment, so today's pain point is cited from the open web instead of a specific thread. The awkwardness of the openssl incantation and the recurring need to monitor expiry are documented in, e.g., [oneuptime: Test SSL cert expiry from the CLI](https://oneuptime.com/blog/post/2026-03-20-test-ssl-cert-expiry-cli/view), [nixCraft: check TLS/SSL certificate expiration from the Linux CLI](https://www.cyberciti.biz/faq/find-check-tls-ssl-certificate-expiry-date-from-linux-unix/), and [ShellHacks: OpenSSL check certificate expiration](https://www.shellhacks.com/openssl-check-ssl-certificate-expiration-date/).

## Install / run

Python 3.8+, standard library only. No dependencies.

```sh
python3 certcheck.py --help
# or
chmod +x certcheck.py && ./certcheck.py example.com
```

## Usage

```sh
# One or more hosts; ports and pasted URLs are fine
certcheck.py example.com api.example.com:8443 https://internal.example.com/login

# Read hosts from a file (one per line, # comments), warn at 14 days
certcheck.py -f hosts.txt --warn 14

# JSON for scripting
certcheck.py example.com --json

# Through a corporate proxy (or set HTTPS_PROXY)
certcheck.py example.com --proxy proxy.corp:3128
```

Example output:

```
HOST                STATUS     DAYS  EXPIRES               ISSUER
github.com:443      OK           87  2026-09-30 23:59 UTC  Sectigo Limited
old.example.com:443 EXPIRED     -12  2026-06-24 09:00 UTC  Let's Encrypt (certificate has expired)
```

## Exit codes (cron/CI-friendly)

| Code | Meaning |
|------|---------|
| 0 | all certificates OK |
| 1 | at least one cert expires within `--warn` days (default 30) |
| 2 | at least one cert expired, invalid, or unreachable |

So a nightly cron line like `certcheck.py -f prod-hosts.txt --warn 21 || notify` is all you need.

## Notes

- Hosts are checked concurrently (up to 8 at a time).
- If a cert fails verification (e.g. already expired), certcheck retries without verification so it can still tell you *when* it expired. That fallback uses a private-but-stable CPython decode helper; if unavailable, it degrades to reporting the verification error.
- `--warn`, `--timeout`, `--no-color`, and `--json` cover the common knobs.

## Tests

```sh
python3 -m unittest test_certcheck
```

12 unit tests over the pure helpers (host parsing, date parsing, hosts-file reading, error handling); the network path was verified live against github.com (OK/EXPIRING/ERROR paths and exit codes all exercised).
