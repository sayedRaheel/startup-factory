# envcheck

A tiny zero-dependency pre-flight check that validates your real `.env` file
against a `.env.example` template — so your app **fails fast** instead of
crashing 15 minutes later with a mysterious `undefined`.

## The problem

A recurring developer headache: someone adds a new required environment
variable, forgets to update teammates / CI, and the app boots fine but then
blows up later when `process.env.SOME_KEY` turns out to be `undefined`. The
ideal behavior is to refuse to start and say exactly which variables are
missing. This "fail-late vs. fail-fast" .env pain is widely discussed
(see source below).

## Source

This idea comes from ongoing developer discussion of missing `.env` variables
breaking CI and local dev. Reddit was not reachable from the build sandbox
(blocked for the crawler), so the cited discussion is the developer-community
write-up of the exact same pain point:

- https://dev.to/xserhio/how-to-stop-your-team-from-breaking-ci-with-missing-env-variables-2lbf
- https://dev.to/hrishikesh_dalal_ced8f95e/the-env-disaster-why-your-app-is-a-ticking-time-bomb-and-how-to-fix-it-3egc

## Requirements

Python 3.6+ (standard library only — no `pip install` needed).

## Install / run

```bash
# no install required; just run it
python3 envcheck.py

# optional: make it a command
chmod +x envcheck.py
./envcheck.py
```

## What it checks

Given a template (`.env.example`) and a real env file (`.env`), it reports:

- **MISSING** — keys declared in the template but absent from your `.env`
- **EMPTY** — keys present but set to an empty value
- **EXTRA** — keys in your `.env` that aren't declared in the template
- **parse warnings** — lines that aren't valid `KEY=VALUE`

It exits **non-zero** when problems are found, so it works as a CI step or a
pre-start guard.

## Usage

```
envcheck [-h] [-e ENV] [-x EXAMPLE] [--allow-empty] [--allow-extra]
         [--json] [-q] [--no-color] [--version]

  -e, --env       path to the real env file   (default: .env)
  -x, --example   path to the template file   (default: .env.example)
  --allow-empty   don't treat empty values as a problem
  --allow-extra   don't treat undeclared keys as a problem
  --json          machine-readable JSON report
  -q, --quiet     print nothing; communicate via exit code only
  --no-color      disable ANSI color
```

Exit codes: `0` = all good, `1` = problems found, `2` = usage / IO error.

## Example

`.env.example`:
```
STRIPE_KEY=
DATABASE_URL=
PORT=3000
```

`.env`:
```
STRIPE_KEY=sk_live_123
DATABASE_URL=
EXTRA_DEBUG=1
```

Run:
```
$ python3 envcheck.py
MISSING (1) declared in template, absent from env:
  - PORT
EMPTY (1) present but set to an empty value:
  ~ DATABASE_URL
EXTRA (1) in env but not declared in template:
  + EXTRA_DEBUG

3 problem(s) found (1 missing, 1 empty, 1 extra).
$ echo $?
1
```

Use it as a CI / pre-start guard:
```bash
python3 envcheck.py --quiet || { echo "Fix your .env first"; exit 1; }
```

## Notes

- Supports `KEY=value`, `export KEY=value`, `#` comments, blank lines, and
  single/double-quoted values.
- Tested in the build sandbox across all flags and exit codes (clean,
  missing/empty/extra, bad files, JSON, quiet). Not experimental.
