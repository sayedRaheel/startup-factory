# cronwise

**The problem:** Cron syntax is the interface developers forget every single time. If you only set up a cron job a couple of times a year, you almost certainly Google the syntax again (is Sunday `0` or `7`? which asterisk is the month?) and reach for crontab.guru — which needs a browser and a network connection. `cronwise` does the same job offline, right in your terminal: it explains a cron expression in plain English and lists the next run times.

**Source / inspiration:** ongoing developer complaints about cron syntax being unintuitive and the heavy reliance on crontab.guru — see the discussion summarized in [How to automate cron jobs without breaking your head (dev.to)](https://dev.to/sam_th/how-to-automate-cron-jobs-without-breaking-your-head-stop-guessing-syntax-3a55) and [crontab.guru reviews / alternatives (SaaSHub)](https://www.saashub.com/crontab-guru-reviews).

## Install / run

No installation, no dependencies — just Python 3.8+ (standard library only).

```bash
python3 cronwise.py '*/15 * * * *'
# or make it executable and drop it on your PATH:
chmod +x cronwise.py && mv cronwise.py ~/.local/bin/cronwise
```

## Usage

```
cronwise EXPRESSION [-n N] [--from 'YYYY-MM-DD HH:MM'] [-q]
```

- `EXPRESSION` — a quoted 5-field cron expression or a macro (`@daily`, `@hourly`, `@weekly`, `@monthly`, `@yearly`, `@midnight`).
- `-n, --next N` — how many upcoming run times to show (default 5).
- `--from DATETIME` — compute upcoming runs from a given time instead of now.
- `-q, --quiet` — print only the run times (handy for scripts).

Supported field syntax: `*`, `a`, `a-b`, `a-b/n`, `*/n`, comma lists `a,b,c`, and named months (`JAN`–`DEC`) and weekdays (`SUN`–`SAT`). Sunday may be written as `0` or `7`. When both day-of-month and day-of-week are restricted, the job runs when **either** matches (standard cron semantics).

## Examples

```
$ cronwise '0 9 * * 1-5' -n 3
Expression : 0 9 * * 1-5
Meaning    : At 09:00 on Monday, Tuesday, Wednesday, Thursday, Friday

Next run times (from 2026-06-16 10:00):
  Wed 2026-06-17 09:00
  Thu 2026-06-18 09:00
  Fri 2026-06-19 09:00
```

```
$ cronwise '*/15 * * * *' -q -n 2
  Tue 2026-06-16 10:15
  Tue 2026-06-16 10:30
```

```
$ cronwise '0 0 1 1 *'
Expression : 0 0 1 1 *
Meaning    : At 00:00 on day-of-month 1 in January
...
```

Invalid expressions are rejected with a clear message and a non-zero exit code:

```
$ cronwise '0 0 * * 8'
error: invalid cron expression: value 8 out of range (0-6) in day-of-week field   # exit 1
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0`  | success |
| `1`  | invalid cron expression / no run times found |
| `2`  | bad command-line argument (e.g. unparseable `--from`) |

## Notes / limitations

- `@reboot` is intentionally unsupported (it has no fixed schedule to compute).
- Times are naive/local; no timezone or DST handling.
- Tested in the sandbox against interval, range, list, named-field, macro, and OR-semantics cases plus a suite of malformed inputs — all behaved as expected.

## Tests & changelog

Run the test suite with `python3 -m unittest test_cronwise -v` (12 cases, standard library only). See `CHANGELOG.md` for release notes.
