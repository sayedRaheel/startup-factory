# epochly

Convert Unix timestamps to human-readable dates (and back) **offline, in your
terminal** — without googling "epoch converter" or fighting the `date`
command, whose flags differ between GNU/Linux (`date -d @123`) and BSD/macOS
(`date -r 123`).

## The problem

Reading a raw epoch like `1704067200` (or `1704067200000`, or
`1704067200000000`) out of a log or database is a daily annoyance. The usual
answers are unsatisfying: `date -r` / `date -d` syntax is inconsistent across
platforms (hence the constant Googling), and the popular web tools
([epochconverter.com](https://www.epochconverter.com/),
[unixtimestamp.com](https://www.unixtimestamp.com/)) need a browser and a
network connection. `epochly` does the same job locally, auto-detecting whether
the number is in seconds, milliseconds, microseconds, or nanoseconds.

## Source / inspiration

The reliance on online epoch converters and the cross-platform `date`
inconsistency are long-standing, recurring developer complaints. Reddit JSON
endpoints were not reachable from the build sandbox, so the cited references are
the community write-ups of the exact same pain point:

- The Robservatory — *Convert epoch time to human-readable time in Terminal*: https://robservatory.com/convert-epoch-time-to-human-readable-time-in-terminal/
- commandlinefu — *convert unixtime to human-readable using date*: https://www.commandlinefu.com/commands/view/3188/convert-unixtime-to-human-readable
- epochconverter.com (illustrates how widely a converter is needed): https://www.epochconverter.com/

## Requirements

Python 3.7+ (standard library only — no `pip install`). The optional `--tz`
flag uses the `zoneinfo` module and needs Python 3.9+ with an IANA tz database
available; without it, UTC and local time still work.

## Install / run

```bash
# run directly
python3 epochly.py 1704067200

# or make it a command on your PATH
chmod +x epochly.py
ln -s "$(pwd)/epochly.py" ~/.local/bin/epochly
epochly 1704067200
```

## Usage

```
epochly [options] [now | diff A B | VALUE]
```

| Form | What it does |
|------|--------------|
| `epochly VALUE` | Convert an epoch number **or** a date string (auto-detected). |
| `epochly now` | Show the current time in every format. |
| `epochly diff A B` | Human-readable duration between two instants. |

Options: `--tz ZONE`, `--format STRFTIME`, `--unit {s,ms,us,ns}`, `--json`,
`--utc`, `--version`, `--help`.

## Examples

```bash
$ epochly 1704067200
       Epoch (s) : 1704067200
      Epoch (ms) : 1704067200000
   Detected unit : s
  ISO 8601 (UTC) : 2024-01-01T00:00:00Z
ISO 8601 (local) : 2024-01-01T00:00:00+00:00
        RFC 2822 : Mon, 01 Jan 2024 00:00:00 +0000
         Weekday : Monday
        Relative : 2 years ago

# milliseconds are auto-detected from the digit count
$ epochly 1704067200000

# date string -> epoch
$ epochly '2024-01-01T00:00:00Z'

# current time in another zone, machine-readable
$ epochly now --tz America/New_York --json

# how far apart are two timestamps?
$ epochly diff 1704067200 1704153600
1 day (86400s)  [B is after A]

# force a unit and use a custom format
$ epochly 1704067200 --unit ms --format '%Y/%m/%d %H:%M'
```

## Unit auto-detection

Based on the integer digit count (the same heuristic the web converters use):

| Digits | Assumed unit |
|--------|--------------|
| ≤ 11 | seconds |
| 12–14 | milliseconds |
| 15–17 | microseconds |
| ≥ 18 | nanoseconds |

Override anytime with `--unit`.

## Exit codes

- `0` — success
- `1` — bad input (unparseable date, unknown timezone, out-of-range timestamp)
- `2` — no arguments (help is printed)

## Tests

```bash
python3 -m unittest -v test_epochly
```

22 tests cover unit detection, epoch↔date conversion, parsing, humanization,
round-tripping, and the CLI. Tested clean on Python 3.10.
