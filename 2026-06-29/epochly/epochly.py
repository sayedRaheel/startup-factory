#!/usr/bin/env python3
"""epochly - an offline, cross-platform Unix-timestamp / date converter.

Adds date-string parsing (so you can also go date -> epoch), relative phrasing
("2 hours ago"), named-timezone output, and custom strftime formatting on top
of the numeric conversion core. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta

__version__ = "0.2.0"

try:  # Python 3.9+
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    _HAVE_ZONEINFO = True
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore
    ZoneInfoNotFoundError = Exception  # type: ignore
    _HAVE_ZONEINFO = False

_UNIT_DIVISOR = {
    "s": 1,
    "ms": 1_000,
    "us": 1_000_000,
    "ns": 1_000_000_000,
}

_NUMERIC_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")


def detect_unit(raw: str) -> str:
    """Guess the unit of a numeric epoch from its digit count."""
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
    """Convert a numeric epoch string to an aware UTC datetime."""
    use_unit = unit or detect_unit(raw)
    if use_unit not in _UNIT_DIVISOR:
        raise ValueError(f"unknown unit: {use_unit!r} (expected s, ms, us or ns)")
    seconds = float(raw) / _UNIT_DIVISOR[use_unit]
    try:
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError(f"timestamp out of range: {raw} ({use_unit})") from exc
    return dt, use_unit


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
    """Parse an ISO-8601 or common human date string into an aware datetime."""
    text = raw.strip()
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


def humanize_delta(delta: timedelta) -> str:
    """Render a timedelta as a compact phrase like '3 hours ago'."""
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
        if len(parts) == 2:
            break
    phrase = ", ".join(parts)
    return f"in {phrase}" if future else f"{phrase} ago"


def _in_named_tz(dt_utc: datetime, tz: str) -> str:
    if not _HAVE_ZONEINFO:
        raise ValueError(
            "--tz requires Python 3.9+ with the zoneinfo module / tz database"
        )
    try:
        return dt_utc.astimezone(ZoneInfo(tz)).isoformat()
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown timezone: {tz!r}") from exc


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epochly",
        description="Offline Unix-timestamp <-> date converter. "
                    "Auto-detects seconds/millis/micros/nanos.",
    )
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    parser.add_argument("value", nargs="?",
                        help="epoch number, date string, or 'now'")
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
    if not args.value:
        parser.print_help()
        return 2
    try:
        return cmd_convert(args)
    except ValueError as exc:
        print(f"epochly: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
