#!/usr/bin/env python3
"""jsondiff - a semantic, offline JSON diff for your terminal.

Standard text diff (`diff`, `git diff`) compares JSON line-by-line, so it lights
up the whole file when keys are merely reordered or one side is minified while
the other is pretty-printed. jsondiff parses both sides into data structures
first and reports only the *semantic* differences.

Zero third-party dependencies - Python standard library only.

NOTE: scaffold - CLI plumbing and IO are in place; the recursive diff engine
lands in the next commit. For now it only reports whether the two documents are
equal as a whole.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, List, Tuple

__version__ = "1.0.0"

# Exit codes (chosen to be script/CI friendly, like `diff` itself):
EXIT_SAME = 0      # inputs are semantically identical
EXIT_DIFF = 1      # inputs differ
EXIT_ERROR = 2     # something went wrong (bad args, unreadable/invalid JSON)


class Change:
    """A single semantic difference between two JSON documents."""

    __slots__ = ("op", "path", "old", "new")

    def __init__(self, op: str, path: str, old: Any = None, new: Any = None):
        self.op = op  # "added" | "removed" | "changed"
        self.path = path
        self.old = old
        self.new = new

    def as_dict(self) -> dict:
        d: dict = {"op": self.op, "path": self.path}
        if self.op in ("removed", "changed"):
            d["old"] = self.old
        if self.op in ("added", "changed"):
            d["new"] = self.new
        return d


def diff(a: Any, b: Any, ignore_array_order: bool = False) -> List[Change]:
    """Return the list of semantic changes turning `a` into `b`.

    Scaffold implementation: whole-document equality only. Replaced by a
    recursive engine in the next commit.
    """
    if a == b:
        return []
    return [Change("changed", "root", a, b)]


def _load(source: str) -> Tuple[Any, str]:
    """Load JSON from a path or '-' for stdin. Returns (data, label)."""
    if source == "-":
        return json.loads(sys.stdin.read()), "<stdin>"
    with open(source, "r", encoding="utf-8") as fh:
        return json.load(fh), source


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jsondiff",
        description=(
            "Semantic diff for two JSON files. Compares parsed data, so "
            "key reordering and pretty/minified formatting are ignored - "
            "you only see real changes."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("left", help="first JSON file (use '-' for stdin)")
    p.add_argument("right", help="second JSON file (use '-' for stdin)")
    p.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        a, la = _load(args.left)
        b, lb = _load(args.right)
    except FileNotFoundError as e:
        print(f"jsondiff: file not found: {e.filename}", file=sys.stderr)
        return EXIT_ERROR
    except json.JSONDecodeError as e:
        print(f"jsondiff: invalid JSON: {e}", file=sys.stderr)
        return EXIT_ERROR

    changes = diff(a, b)
    if not changes:
        print(f"No differences ({la} == {lb}).")
        return EXIT_SAME
    print(f"{len(changes)} difference(s).")
    return EXIT_DIFF


if __name__ == "__main__":
    sys.exit(main())
