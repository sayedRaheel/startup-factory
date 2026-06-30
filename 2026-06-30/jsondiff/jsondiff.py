#!/usr/bin/env python3
"""jsondiff - a semantic, offline JSON diff for your terminal.

Standard text diff (`diff`, `git diff`) compares JSON line-by-line, so it lights
up the whole file when keys are merely reordered or one side is minified while
the other is pretty-printed. jsondiff parses both sides into data structures
first and reports only the *semantic* differences: which keys were added or
removed and which values changed, each with a JSON path so you can find it.

Zero third-party dependencies - Python standard library only.
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


# --------------------------------------------------------------------------- #
# Diff model
# --------------------------------------------------------------------------- #
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


def _join(path: str, key: Any, is_index: bool) -> str:
    """Build a JSON-path-ish string, e.g. root.users[0].name."""
    if is_index:
        return f"{path}[{key}]"
    # Use bracket+quote notation for keys that are not simple identifiers.
    skey = str(key)
    if skey.isidentifier():
        return f"{path}.{skey}" if path else skey
    safe = skey.replace("\\", "\\\\").replace('"', '\\"')
    return f'{path}["{safe}"]' if path else f'["{safe}"]'


def _canonical(value: Any) -> str:
    """A stable string key for a value, used for order-insensitive array diff."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Core comparison
# --------------------------------------------------------------------------- #
def diff(a: Any, b: Any, ignore_array_order: bool = False) -> List[Change]:
    """Return the list of semantic changes turning `a` into `b`."""
    changes: List[Change] = []
    _diff(a, b, "root", ignore_array_order, changes)
    return changes


def _diff(a: Any, b: Any, path: str, iao: bool, out: List[Change]) -> None:
    # Different fundamental types => a single "changed".
    if type(a) is not type(b) and not _both_numbers(a, b):
        out.append(Change("changed", path, a, b))
        return

    if isinstance(a, dict):
        _diff_dict(a, b, path, iao, out)
    elif isinstance(a, list):
        _diff_list(a, b, path, iao, out)
    else:
        if a != b:
            out.append(Change("changed", path, a, b))


def _both_numbers(a: Any, b: Any) -> bool:
    # Treat 1 and 1.0 as comparable numbers (bool is excluded on purpose).
    num = (int, float)
    return (
        isinstance(a, num)
        and isinstance(b, num)
        and not isinstance(a, bool)
        and not isinstance(b, bool)
    )


def _diff_dict(a: dict, b: dict, path: str, iao: bool, out: List[Change]) -> None:
    for key in a:
        child = _join(path, key, is_index=False)
        if key not in b:
            out.append(Change("removed", child, old=a[key]))
        else:
            _diff(a[key], b[key], child, iao, out)
    for key in b:
        if key not in a:
            child = _join(path, key, is_index=False)
            out.append(Change("added", child, new=b[key]))


def _diff_list(a: list, b: list, path: str, iao: bool, out: List[Change]) -> None:
    if iao:
        _diff_list_unordered(a, b, path, out)
        return
    common = min(len(a), len(b))
    for i in range(common):
        _diff(a[i], b[i], _join(path, i, is_index=True), iao, out)
    for i in range(common, len(a)):
        out.append(Change("removed", _join(path, i, is_index=True), old=a[i]))
    for i in range(common, len(b)):
        out.append(Change("added", _join(path, i, is_index=True), new=b[i]))


def _diff_list_unordered(a: list, b: list, path: str, out: List[Change]) -> None:
    """Compare arrays as multisets: only membership matters, not position."""
    from collections import Counter

    ca = Counter(_canonical(x) for x in a)
    cb = Counter(_canonical(x) for x in b)
    by_key_a = {}
    by_key_b = {}
    for x in a:
        by_key_a.setdefault(_canonical(x), x)
    for x in b:
        by_key_b.setdefault(_canonical(x), x)

    removed = ca - cb  # elements present more often in `a`
    added = cb - ca    # elements present more often in `b`
    for k in sorted(removed):
        for _ in range(removed[k]):
            out.append(Change("removed", f"{path}[*]", old=by_key_a[k]))
    for k in sorted(added):
        for _ in range(added[k]):
            out.append(Change("added", f"{path}[*]", new=by_key_b[k]))


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
_COLORS = {"added": "\033[32m", "removed": "\033[31m", "changed": "\033[33m"}
_RESET = "\033[0m"
_SIGN = {"added": "+", "removed": "-", "changed": "~"}


def _fmt_val(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def render_text(changes: List[Change], use_color: bool) -> str:
    lines: List[str] = []
    for c in sorted(changes, key=lambda x: x.path):
        sign = _SIGN[c.op]
        color = _COLORS[c.op] if use_color else ""
        reset = _RESET if use_color else ""
        if c.op == "added":
            body = f"{c.path} = {_fmt_val(c.new)}"
        elif c.op == "removed":
            body = f"{c.path} = {_fmt_val(c.old)}"
        else:
            body = f"{c.path}: {_fmt_val(c.old)} -> {_fmt_val(c.new)}"
        lines.append(f"{color}{sign} {body}{reset}")
    return "\n".join(lines)


def summary(changes: List[Change]) -> str:
    counts = {"added": 0, "removed": 0, "changed": 0}
    for c in changes:
        counts[c.op] += 1
    return (
        f"{len(changes)} difference(s): "
        f"{counts['added']} added, "
        f"{counts['removed']} removed, "
        f"{counts['changed']} changed"
    )


# --------------------------------------------------------------------------- #
# IO + CLI
# --------------------------------------------------------------------------- #
def _load(source: str) -> Tuple[Any, str]:
    """Load JSON from a path or '-' for stdin. Returns (data, label)."""
    if source == "-":
        text = sys.stdin.read()
        return json.loads(text), "<stdin>"
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
        epilog=(
            "Exit codes: 0 = identical, 1 = differences found, 2 = error.\n"
            "Examples:\n"
            "  jsondiff old.json new.json\n"
            "  curl -s api/a | jsondiff - b.json --ignore-array-order\n"
            "  jsondiff a.json b.json --format json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("left", help="first JSON file (use '-' for stdin)")
    p.add_argument("right", help="second JSON file (use '-' for stdin)")
    p.add_argument(
        "--ignore-array-order",
        action="store_true",
        help="treat arrays as unordered (compare membership, not position)",
    )
    p.add_argument(
        "-f",
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    p.add_argument(
        "--no-color",
        action="store_true",
        help="disable ANSI colors in text output",
    )
    p.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="print nothing; communicate via exit code only",
    )
    p.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.left == "-" and args.right == "-":
        parser.error("only one of LEFT/RIGHT may read from stdin ('-')")

    try:
        a, la = _load(args.left)
        b, lb = _load(args.right)
    except FileNotFoundError as e:
        print(f"jsondiff: file not found: {e.filename}", file=sys.stderr)
        return EXIT_ERROR
    except json.JSONDecodeError as e:
        print(f"jsondiff: invalid JSON: {e}", file=sys.stderr)
        return EXIT_ERROR
    except OSError as e:
        print(f"jsondiff: cannot read input: {e}", file=sys.stderr)
        return EXIT_ERROR

    changes = diff(a, b, ignore_array_order=args.ignore_array_order)

    if args.quiet:
        return EXIT_SAME if not changes else EXIT_DIFF

    if args.format == "json":
        print(json.dumps([c.as_dict() for c in changes], indent=2, ensure_ascii=False))
    else:
        if not changes:
            print(f"No differences ({la} == {lb}).")
        else:
            use_color = (not args.no_color) and sys.stdout.isatty()
            print(render_text(changes, use_color))
            print(f"\n{summary(changes)}")

    return EXIT_SAME if not changes else EXIT_DIFF


if __name__ == "__main__":
    sys.exit(main())
