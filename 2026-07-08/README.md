# jwtpeek

Decode and inspect JSON Web Tokens **locally** — never paste a production
token into jwt.io again.

**The problem:** debugging auth means constantly peeking inside JWTs, and the
reflex is to paste them into a web decoder. But JWTs are live credentials;
pasting real ones into a website is a leak waiting to happen. This annoyance
comes up constantly in developer forums — people trade one-liner shell hacks
for it that break on missing base64 padding.

**Source:** Reddit is not crawlable from this run's sandbox, so no direct
thread URL; the same pain point is documented in these public discussions:
[Simple Command Line Function to Decode JWTs](https://www.pgrs.net/2022/06/02/simple-command-line-function-to-decode-jwts/)
and this widely-shared [decode-a-JWT gist](https://gist.github.com/angelo-v/e0208a18d455e2e6ea3c40ad637aac53)
(and its comment thread of broken variants).

## Install / run

Single file, Python 3.8+, standard library only:

```sh
python3 jwtpeek.py <token>
# or
chmod +x jwtpeek.py && ./jwtpeek.py <token>
```

## Usage

```sh
jwtpeek eyJhbGciOi...              # pretty-print header, payload, time claims
pbpaste | jwtpeek                  # read from stdin (clipboard, curl, logs)
jwtpeek -f token.txt               # read from a file
jwtpeek --json TOKEN | jq .payload # machine-readable output
jwtpeek --check-exp TOKEN          # exit 1 if expired — CI/script friendly
jwtpeek --verify SECRET TOKEN      # verify an HS256 signature (stdlib hmac)
```

Niceties: tolerates a `Bearer ` prefix and missing base64url padding,
humanizes `exp`/`iat`/`nbf` ("in 119m", "3d ago"), flags expired tokens,
and uses constant-time comparison for signature checks.

Exit codes: `0` OK · `1` expired or bad signature (when checked) · `2` bad input.

## Example

```
$ jwtpeek $TOKEN
Header:
{ "alg": "HS256", "typ": "JWT" }

Payload:
{ "exp": 1783520156, "iat": 1783512856, "role": "admin", "sub": "sayed" }

Time claims:
  exp: 2026-07-08 14:15:56 UTC (in 119m)
  iat: 2026-07-08 12:14:16 UTC (100s ago)
  status: not expired
```

## Tests

```sh
python3 test_jwtpeek.py   # 15 tests, no network, no dependencies
```

## Notes

- Decoding does **not** validate the signature (that's the point — it's an
  inspector). `--verify` supports HS256 only; RS/ES tokens are decode-only.
- Built and tested automatically on 2026-07-08 by a scheduled agent run.
