#!/usr/bin/env python3
"""epochly - an offline, cross-platform Unix-timestamp / date converter.

Stop googling "epoch converter". `epochly` turns a Unix timestamp into a
human-readable date (and back) right in your terminal, with no dependence on
the inconsistent `date -r` flags that differ between GNU/Linux and BSD/macOS.

Standard library only. No pip install required.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta

__version__ = "1.0.0"

# Try to make named-timezone (--tz) support available, but degrade gracefully
# on systems whose Python lacks zoneinfo or the IANA tz database.
try:  # Python 3.9+
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    _HAVE_ZONEINFO = True
except Exception:  # pragma: no cover - exercised only on older runtimes
    ZoneInfo = None  # type: ignore
    ZoneInfoNotFoundError = Exception  # type: ignore
    _HAVE_ZONEINFO = False


# --------------------------------------------------------------------------- #
# Numeric epoch handling
# --------------------------------------------------------------------------- #

# Map of unit -> divisor to reach seconds. The detection below is based on the
# digit count of the integer part, the same heuristic epochconverter.com uses.
_UNIT_DIVISOR = {
    "s": 1,
    "ms": 1_000,
    "us": 1_000_000,
    "ns": 1_000_000_000,
}

_NUMERIC_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")


def detect_unit(raw: str) -> str:
    """Guess the unit of a numeric epoch from its digit count.

    <= 11 digits  -> seconds        (good until the year 5138)
    12-14 digits  -> milliseconds
    15-17 digits  -> microseconds
    >= 18 digits  -> nanoseconds
    """
    digits = re.sub(r"[^\d]", "", raw.split(".")[0])
    n = len(digits)
    if n <= 11:
        return "s"
    if n <= 14:
        return "ms"
    if n <= 17:
        return "us"
    return "ns"


def epoch_to_datetime(raw: str, unit: str | None) -> tuple[datetime, str]:
    """Convert a numeric epoch string to an aware UTC datetime.

    Returns (utc_datetime, unit_used).
    """
    use_unit = unit or detect_unit(raw)
    if use_unit not in _UNIT_DIVISOR:
        raise ValueError(f"unknown unit: {use_unit!r} (expected s, ms, us or ns)")
    seconds = float(raw) / _UNIT_DIVISOR[use_unit]
    try:
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError(f"timestamp out of range: {raw} ({use_unit})") from exc
    return dt, use_unit


# --------------------------------------------------------------------------- #
# Date-string parsing
# --------------------------------------------------------------------------- #

_FALLBACK_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
    "%b %d %Y",
    "%b %d, %Y",
    "%d %b %Y",
    "%a %b %d %H:%M:%S %Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
)


def parse_datestring(raw: str) -> datetime:
    """Parse an ISO-8601 or common human date string into an aware datetime.

    Naive inputs (no offset) are assumed to be UTC.
    """
    text = raw.strip()

    # datetime.fromisoformat is the most permissive; normalise a trailing Z.
    iso_candidate = text
    if iso_candidate.endswith(("Z", "z")):
        iso_candidate = iso_candidate[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(iso_candidate)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    for fmt in _FALLBACK_FORMATS:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    raise ValueError(f"could not parse date string: {raw!r}")


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #

def humanize_delta(delta: timedelta) -> str:
    """Render a timedelta as a compact, human phrase like '3 hours ago'."""
    total = delta.total_seconds()
    future = total > 0
    secs = abs(int(round(total)))
    if secs == 0:
        return "just now"

    units = (
        ("year", 365 * 24 * 3600),
        ("day", 24 * 3600),
        ("hour", 3600),
        ("minute", 60),
        ("second", 1),
    )
    parts: list[str] = []
    remaining = secs
    for name, size in units:
        if remaining >= size:
            qty, remaining = divmod(remaining, size)
            parts.append(f"{qty} {name}{'s' if qty != 1 else ''}")
        if len(parts) == 2:  # keep it to the two most significant units
            break
    phrase = ", ".join(parts)
    return f"in {phrase}" if future else f"{phrase} ago"


def humanize_duration(delta: timedelta) -> str:
    """Render an absolute duration (no 'ago'/'in') for the diff command."""
    secs = abs(int(round(delta.total_seconds())))
    if secs == 0:
        return "0 seconds"
    units = (
        ("day", 24 * 3600),
        ("hour", 3600),
        ("minute", 60),
        ("second", 1),
    )
    parts: list[str] = []
    remaining = secs
    for name, size in units:
        if remaining >= size:
            qty, remaining = divmod(remaining, size)
            parts.append(f"{qty} {name}{'s' if qty != 1 else ''}")
    return ", ".join(parts)


def build_report(dt_utc: datetime, *, tz: str | None, fmt: str | None,
                 unit_used: str | None) -> dict:
    """Build the structured set of representations for one instant."""
    local = dt_utc.astimezone()
    now = datetime.now(timezone.utc)

    report = {
        "epoch_seconds": int(dt_utc.timestamp()),
        "epoch_millis": int(dt_utc.timestamp() * 1000),
        "iso_utc": dt_utc.isoformat().replace("+00:00", "Z"),
        "iso_local": local.isoformat(),
        "rfc2822": dt_utc.strftime("%a, %d %b %Y %H:%M:%S +0000"),
        "weekday": dt_utc.strftime("%A"),
        "relative": humanize_delta(dt_utc - now),
    }
    if unit_used:
        report["detected_unit"] = unit_used
    if fmt:
        report["formatted"] = dt_utc.strftime(fmt)
    if tz:
        report["iso_tz"] = _in_named_tz(dt_utc, tz)
        report["tz"] = tz
    return report


def _in_named_tz(dt_utc: datetime, tz: str) -> str:
    if not _HAVE_ZONEINFO:
        raise ValueError(
            "--tz requires Python 3.9+ with the zoneinfo module / tz database"
        )
    try:
        return dt_utc.astimezone(ZoneInfo(tz)).isoformat()
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown timezone: {tz!r}") from exc


def render_text(report: dict) -> str:
    order = [
        ("epoch_seconds", "Epoch (s)"),
        ("epoch_millis", "Epoch (ms)"),
        ("detected_unit", "Detected unit"),
        ("iso_utc", "ISO 8601 (UTC)"),
        ("iso_local", "ISO 8601 (local)"),
        ("iso_tz", "ISO 8601 (--tz)"),
        ("rfc2822", "RFC 2822"),
        ("weekday", "Weekday"),
        ("relative", "Relative"),
        ("formatted", "Custom format"),
    ]
    width = max(len(label) for _, label in order)
    lines = []
    for key, label in order:
        if key in report:
            lines.append(f"{label.rjust(width)} : {report[key]}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def resolve_instant(value: str, unit: str | None) -> tuple[datetime, str | None]:
    """Turn a CLI value into (utc_datetime, unit_used_or_None)."""
    if value.lower() == "now":
        return datetime.now(timezone.utc), None
    if _NUMERIC_RE.match(value.strip()):
        dt, used = epoch_to_datetime(value.strip(), unit)
        return dt, used
    return parse_datestring(value), None


def cmd_convert(args: argparse.Namespace) -> int:
    dt_utc, unit_used = resolve_instant(args.value, args.unit)
    report = build_report(dt_utc, tz=args.tz, fmt=args.format, unit_used=unit_used)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report))
    return 0


def cmd_now(args: argparse.Namespace) -> int:
    dt_utc = datetime.now(timezone.utc)
    report = build_report(dt_utc, tz=args.tz, fmt=args.format, unit_used=None)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report))
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    a, _ = resolve_instant(args.a, args.unit)
    b, _ = resolve_instant(args.b, args.unit)
    delta = b - a
    seconds = delta.total_seconds()
    if args.json:
        print(json.dumps({
            "a": a.isoformat().replace("+00:00", "Z"),
            "b": b.isoformat().replace("+00:00", "Z"),
            "seconds": seconds,
            "human": humanize_duration(delta),
            "b_after_a": seconds >= 0,
        }, indent=2))
    else:
        direction = "after" if seconds >= 0 else "before"
        print(f"{humanize_duration(delta)} ({seconds:g}s)  [B is {direction} A]")
    return 0


_COMMANDS = ("now", "diff", "convert")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epochly",
        description="Offline Unix-timestamp <-> date converter. "
                    "Auto-detects seconds/millis/micros/nanos.",
        usage="epochly [options] [now | diff A B | VALUE]",
        epilog="commands:\n"
               "  VALUE            convert an epoch number or date string (default)\n"
               "  now              show the current time in every format\n"
               "  diff A B         human-readable duration between two instants\n\n"
               "examples:\n"
               "  epochly 1704067200               # epoch -> dates\n"
               "  epochly 1704067200000            # millis auto-detected\n"
               "  epochly '2024-01-01T00:00:00Z'   # date string -> epoch\n"
               "  epochly now --tz America/New_York\n"
               "  epochly diff 1704067200 1704153600\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    parser.add_argument("args", nargs="*", metavar="ARG",
                        help="command and/or value(s); see commands above")
    parser.add_argument("--utc", action="store_true",
                        help="(default) interpret/show UTC; kept for clarity")
    parser.add_argument("--tz", metavar="ZONE",
                        help="also show the time in a named IANA zone "
                             "(e.g. Europe/Paris); needs Python 3.9+")
    parser.add_argument("--format", metavar="STRFTIME",
                        help="add a custom strftime-formatted line")
    parser.add_argument("--unit", choices=sorted(_UNIT_DIVISOR),
                        help="force the epoch unit instead of auto-detecting")
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    positionals = list(args.args)

    if not positionals:
        parser.print_help()
        return 2

    # Determine the command. A leading 'now'/'diff'/'convert' selects it;
    # anything else is treated as a value for the implicit convert command.
    command = "convert"
    rest = positionals
    if positionals[0].lower() in _COMMANDS:
        command = positionals[0].lower()
        rest = positionals[1:]

    try:
        if command == "now":
            if rest:
                raise ValueError("'now' takes no arguments")
            return cmd_now(args)

        if command == "diff":
            if len(rest) != 2:
                raise ValueError("'diff' needs exactly two arguments: A and B")
            args.a, args.b = rest
            return cmd_diff(args)

        # convert (explicit or implicit)
        if len(rest) != 1:
            raise ValueError(
                "expected a single value to convert (got "
                f"{len(rest)}); quote date strings that contain spaces"
            )
        args.value = rest[0]
        return cmd_convert(args)
    except ValueError as exc:
        print(f"epochly: error: {exc}", file=sys.stderr)
        return 1
    except BrokenPipeError:  # pragma: no cover - piping into head etc.
        return 0


if __name__ == "__main__":
    sys.exit(main())
