#!/usr/bin/env python3
"""epochly - an offline, cross-platform Unix-timestamp / date converter.

Core conversion engine: turn a numeric epoch into a human-readable date,
auto-detecting whether it is in seconds, milliseconds, microseconds, or
nanoseconds. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone

__version__ = "0.1.0"

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


def build_report(dt_utc: datetime, *, unit_used: str | None) -> dict:
    """Build the structured set of representations for one instant."""
    local = dt_utc.astimezone()
    report = {
        "epoch_seconds": int(dt_utc.timestamp()),
        "epoch_millis": int(dt_utc.timestamp() * 1000),
        "iso_utc": dt_utc.isoformat().replace("+00:00", "Z"),
        "iso_local": local.isoformat(),
        "rfc2822": dt_utc.strftime("%a, %d %b %Y %H:%M:%S +0000"),
        "weekday": dt_utc.strftime("%A"),
    }
    if unit_used:
        report["detected_unit"] = unit_used
    return report


def render_text(report: dict) -> str:
    order = [
        ("epoch_seconds", "Epoch (s)"),
        ("epoch_millis", "Epoch (ms)"),
        ("detected_unit", "Detected unit"),
        ("iso_utc", "ISO 8601 (UTC)"),
        ("iso_local", "ISO 8601 (local)"),
        ("rfc2822", "RFC 2822"),
        ("weekday", "Weekday"),
    ]
    width = max(len(label) for _, label in order)
    lines = []
    for key, label in order:
        if key in report:
            lines.append(f"{label.rjust(width)} : {report[key]}")
    return "\n".join(lines)


def cmd_convert(args: argparse.Namespace) -> int:
    dt_utc, unit_used = epoch_to_datetime(args.value.strip(), args.unit)
    report = build_report(dt_utc, unit_used=unit_used)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epochly",
        description="Offline Unix-timestamp converter. "
                    "Auto-detects seconds/millis/micros/nanos.",
    )
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    parser.add_argument("value", nargs="?", help="epoch number to convert")
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
