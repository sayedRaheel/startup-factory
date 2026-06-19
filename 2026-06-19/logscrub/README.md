# logscrub

Redact secrets and PII from logs **before** you paste them into a bug report,
chat, or Stack Overflow question.

## Problem

Developers debugging an issue routinely copy raw logs into GitHub issues, Slack,
or Stack Overflow — and those logs often contain `Authorization: Bearer ...`
headers, API keys, AWS credentials, emails, and IPs. This is one of the most
common ways secrets leak: in 2023 alone, millions of secrets were exposed in
public repos and paste-ups. `logscrub` is a tiny filter that masks that stuff
in one command so you can share logs safely.

Inspired by the recurring "I accidentally pasted a token in my logs" problem
discussed around developer communities and write-ups such as
[5 Ways Developers Accidentally Leak API Keys](https://ax-sentinel.com/blog/prevent-api-key-leaks-llm-prompts)
and [How They Leak and How Developers Can Avoid It](https://medium.com/@cyb3rzee/api-keys-tokens-and-secrets-how-they-leak-and-how-developers-can-avoid-it-b28fd6ee40a6).

## Install

No dependencies — just Python 3.7+ (standard library only).

```bash
chmod +x logscrub.py
# optional: put it on your PATH
cp logscrub.py ~/.local/bin/logscrub
```

## Usage

```bash
# pipe logs through it
cat app.log | logscrub

# scrub a file to a new file
logscrub app.log -o app.clean.log

# edit files in place
logscrub *.log --in-place

# only some detector types, with a summary
logscrub app.log --only aws_access_key,jwt,bearer_token --stats

# skip a noisy detector
logscrub app.log --skip ipv4

# custom mask
logscrub app.log --mask 'XXX'

# list everything it can detect
logscrub --list-types
```

Reads from stdin when no files are given, so it drops into any pipeline.

## What it detects

`private_key`, `jwt`, `github_token`, `slack_token`, `aws_access_key`,
`google_api_key`, `stripe_key`, `bearer_token`, `generic_secret`
(`api_key=`, `password=`, `token=`, ...), `credit_card` (Luhn-validated),
`email`, `ipv4`.

For labelled assignments (e.g. `password=Hunter2`) only the value is masked, so
the surrounding context stays readable: `password=[REDACTED:generic_secret]`.

## Example

```
$ logscrub sample.log --stats
2026-06-19 10:02:11 INFO  request from [REDACTED:ipv4] user=[REDACTED:email]
2026-06-19 10:02:11 DEBUG Authorization: Bearer [REDACTED:bearer_token]
2026-06-19 10:02:12 DEBUG aws_key=[REDACTED:aws_access_key] region=us-east-1
2026-06-19 10:02:12 WARN  password=[REDACTED:generic_secret] retry=0
2026-06-19 10:02:13 INFO  payment card [REDACTED:credit_card] approved
logscrub: redactions by type:
  aws_access_key   1
  bearer_token     1
  ...
```

## Exit codes

`0` success · `1` I/O error (unreadable/unwritable file) · `2` bad arguments
(e.g. an unknown `--only`/`--skip` type).

## Tests

```bash
python3 test_logscrub.py
```

12 unit tests covering each detector, Luhn validation, `--only`/`--skip`,
custom masks, and the clean-text-unchanged case.

## Caveats

Regex-based redaction is **best-effort**, not a security guarantee. It will
catch common, well-formed secrets but cannot recognise every possible token
shape or a high-entropy string with no label. Always eyeball the output before
sharing sensitive logs.
