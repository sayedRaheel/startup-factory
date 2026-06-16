#!/usr/bin/env python3
"""
cronwise - explain a cron expression in plain English and show its next run times.

An offline, dependency-free alternative to crontab.guru for the times you just
want to sanity-check a cron line without opening a browser.

Supports standard 5-field cron expressions:

    ┌───────────── minute        (0-59)
    │ ┌───────────── hour        (0-23)
    │ │ ┌───────────── day-of-month (1-31)
    │ │ │ ┌───────────── month     (1-12 or JAN-DEC)
    │ │ │ │ ┌───────────── day-of-week (0-6, 0=Sunday, or SUN-SAT; 7 also = Sunday)
    │ │ │ │ │
    * * * * *

Field syntax: *  a  a-b  a-b/n  */n  a,b,c  and named months/days.
Macros: @yearly @annually @monthly @weekly @daily @midnight @hourly.

No third-party dependencies - Python 3.8+ standard library only.
"""

import argparse
import sys
from datetime import datetime, timedelta

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# Field definitions
# ---------------------------------------------------------------------------

MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
DOW_NAMES = {
    "sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6,
}
DOW_DISPLAY = ["Sunday", "Monday", "Tuesday", "Wednesday",
               "Thursday", "Friday", "Saturday"]
MONTH_DISPLAY = ["", "January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]

MACROS = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}

# (name, min, max, names-map)
FIELDS = [
    ("minute", 0, 59, None),
    ("hour", 0, 23, None),
    ("day-of-month", 1, 31, None),
    ("month", 1, 12, MONTH_NAMES),
    ("day-of-week", 0, 6, DOW_NAMES),
]


class CronError(ValueError):
    """Raised when a cron expression cannot be parsed."""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _resolve_token(tok, names):
    """Turn a token (possibly a name) into an int."""
    low = tok.lower()
    if names and low in names:
        return names[low]
    try:
        return int(tok)
    except ValueError:
        raise CronError(f"'{tok}' is not a valid number or name")


def parse_field(expr, fmin, fmax, names, field_name):
    """Parse one cron field into a sorted set of allowed integer values."""
    allowed = set()
    for part in expr.split(","):
        part = part.strip()
        if part == "":
            raise CronError(f"empty value in {field_name} field")

        step = 1
        if "/" in part:
            base, _, step_s = part.partition("/")
            if step_s == "" or not step_s.isdigit() or int(step_s) == 0:
                raise CronError(f"invalid step '{part}' in {field_name} field")
            step = int(step_s)
        else:
            base = part

        if base == "*":
            lo, hi = fmin, fmax
        elif "-" in base:
            lo_s, _, hi_s = base.partition("-")
            lo = _resolve_token(lo_s, names)
            hi = _resolve_token(hi_s, names)
        else:
            val = _resolve_token(base, names)
            # day-of-week: 7 is an alias for Sunday (0)
            if field_name == "day-of-week" and val == 7:
                val = 0
            lo = hi = val

        if field_name == "day-of-week":
            if lo == 7:
                lo = 0
            if hi == 7:
                hi = 0

        if lo > hi:
            raise CronError(
                f"range start {lo} is greater than end {hi} in {field_name} field")
        for v in range(lo, hi + 1, step):
            if v < fmin or v > fmax:
                raise CronError(
                    f"value {v} out of range ({fmin}-{fmax}) in {field_name} field")
            allowed.add(v)

    return allowed


def parse_cron(expression):
    """Parse a full cron expression (or macro) into a dict of field-name -> set."""
    expression = expression.strip()
    if not expression:
        raise CronError("empty cron expression")

    if expression.startswith("@"):
        macro = expression.lower()
        if macro == "@reboot":
            raise CronError("@reboot has no fixed schedule and cannot be computed")
        if macro not in MACROS:
            raise CronError(f"unknown macro '{expression}'")
        expression = MACROS[macro]

    parts = expression.split()
    if len(parts) != 5:
        raise CronError(
            f"expected 5 fields, got {len(parts)}: {' '.join(parts)!r}")

    result = {}
    for value, (name, fmin, fmax, names) in zip(parts, FIELDS):
        result[name] = parse_field(value, fmin, fmax, names, name)
    # keep the raw fields around for description logic
    result["_raw"] = dict(zip([f[0] for f in FIELDS], parts))
    return result


# ---------------------------------------------------------------------------
# Next-run computation
# ---------------------------------------------------------------------------

def _matches(dt, parsed):
    dom = parsed["_raw"]["day-of-month"]
    dow = parsed["_raw"]["day-of-week"]
    cron_dow = dt.weekday()  # Mon=0..Sun=6
    cron_dow = (cron_dow + 1) % 7  # convert to Sun=0..Sat=6

    minute_ok = dt.minute in parsed["minute"]
    hour_ok = dt.hour in parsed["hour"]
    month_ok = dt.month in parsed["month"]
    dom_ok = dt.day in parsed["day-of-month"]
    dow_ok = cron_dow in parsed["day-of-week"]

    # Cron semantics: if BOTH day-of-month and day-of-week are restricted
    # (not '*'), the job runs when EITHER matches. Otherwise both must match.
    if dom != "*" and dow != "*":
        day_ok = dom_ok or dow_ok
    else:
        day_ok = dom_ok and dow_ok

    return minute_ok and hour_ok and month_ok and day_ok


def next_runs(parsed, start, count):
    """Yield the next `count` datetimes (after `start`) that match."""
    # round up to the next whole minute
    dt = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
    found = []
    # search a generous horizon: up to ~8 years of minutes
    limit = 8 * 366 * 24 * 60
    steps = 0
    while len(found) < count and steps < limit:
        if _matches(dt, parsed):
            found.append(dt)
        dt += timedelta(minutes=1)
        steps += 1
    return found


# ---------------------------------------------------------------------------
# Plain-English description
# ---------------------------------------------------------------------------

def _describe_field_list(values, fmt):
    vals = sorted(values)
    return ", ".join(fmt(v) for v in vals)


def describe(parsed):
    raw = parsed["_raw"]
    minute, hour = raw["minute"], raw["hour"]
    dom, month, dow = raw["day-of-month"], raw["month"], raw["day-of-week"]

    # ---- time of day ----
    if minute == "*" and hour == "*":
        time_part = "every minute"
    elif hour == "*" and minute.startswith("*/"):
        time_part = f"every {minute[2:]} minutes"
    elif minute.startswith("*/") and hour == "*":
        time_part = f"every {minute[2:]} minutes"
    elif minute == "0" and hour == "*":
        time_part = "every hour, on the hour"
    elif hour == "*":
        time_part = f"at minute {_describe_field_list(parsed['minute'], str)} of every hour"
    elif "," not in minute and "-" not in minute and "/" not in minute \
            and "," not in hour and "-" not in hour and "/" not in hour:
        time_part = f"at {int(hour):02d}:{int(minute):02d}"
    else:
        mins = _describe_field_list(parsed["minute"], str)
        hours = _describe_field_list(parsed["hour"], str)
        time_part = f"at minute(s) {mins} past hour(s) {hours}"

    # ---- day-of-week ----
    if dow == "*":
        dow_part = ""
    else:
        names = _describe_field_list(parsed["day-of-week"], lambda v: DOW_DISPLAY[v])
        dow_part = f"on {names}"

    # ---- day-of-month ----
    if dom == "*":
        dom_part = ""
    elif dom.startswith("*/"):
        dom_part = f"every {dom[2:]} days of the month"
    else:
        dom_part = f"on day-of-month {_describe_field_list(parsed['day-of-month'], str)}"

    # ---- month ----
    if month == "*":
        month_part = ""
    else:
        names = _describe_field_list(parsed["month"], lambda v: MONTH_DISPLAY[v])
        month_part = f"in {names}"

    pieces = [time_part]
    # day clause: combine dom and dow sensibly
    if dom_part and dow_part:
        pieces.append(f"{dom_part} and {dow_part}")
    elif dom_part:
        pieces.append(dom_part)
    elif dow_part:
        pieces.append(dow_part)
    if month_part:
        pieces.append(month_part)

    sentence = " ".join(pieces)
    return sentence[0].upper() + sentence[1:]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="cronwise",
        description="Explain a cron expression in plain English and show its "
                    "next run times. Offline, no dependencies.",
        epilog="Examples:\n"
               "  cronwise '*/15 * * * *'\n"
               "  cronwise '0 9 * * 1-5' -n 3\n"
               "  cronwise @daily\n"
               "  cronwise '0 0 1 1 *' --from '2026-12-31 23:00'\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("expression",
                   help="cron expression (quote it) or a macro like @daily")
    p.add_argument("-n", "--next", type=int, default=5, metavar="N",
                   dest="count",
                   help="number of upcoming run times to show (default: 5)")
    p.add_argument("--from", dest="from_time", metavar="DATETIME",
                   help="compute next runs starting from this time "
                        "(format 'YYYY-MM-DD HH:MM'); defaults to now")
    p.add_argument("-q", "--quiet", action="store_true",
                   help="only print next run times (no description)")
    p.add_argument("--version", action="version",
                   version=f"%(prog)s {__version__}")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.count < 0:
        print("error: --next must be >= 0", file=sys.stderr)
        return 2

    try:
        parsed = parse_cron(args.expression)
    except CronError as e:
        print(f"error: invalid cron expression: {e}", file=sys.stderr)
        return 1

    if args.from_time:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
            try:
                start = datetime.strptime(args.from_time, fmt)
                break
            except ValueError:
                start = None
        if start is None:
            print(f"error: could not parse --from value {args.from_time!r} "
                  f"(use 'YYYY-MM-DD HH:MM')", file=sys.stderr)
            return 2
    else:
        start = datetime.now()

    if not args.quiet:
        print(f"Expression : {args.expression}")
        print(f"Meaning    : {describe(parsed)}")
        print()

    if args.count > 0:
        runs = next_runs(parsed, start, args.count)
        if not runs:
            print("No matching run times found within the search horizon.",
                  file=sys.stderr)
            return 1
        header = "Next run times" if not args.quiet else None
        if header:
            print(f"{header} (from {start.strftime('%Y-%m-%d %H:%M')}):")
        for dt in runs:
            print(f"  {dt.strftime('%a %Y-%m-%d %H:%M')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
