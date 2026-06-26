#!/usr/bin/env python3
"""mdtable - pretty-print and align GitHub-Flavored Markdown tables.

Hand-aligning Markdown tables is tedious: every time you add a row or widen a
cell you have to re-pad every pipe by hand. mdtable finds the tables in a
Markdown document and re-pads them so the columns line up, while honoring the
per-column alignment markers (:---, :---:, ---:). Non-table lines are left
exactly as they were.

Standard library only. No dependencies.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from typing import List, Optional, Tuple

__version__ = "1.0.0"

# Exit codes
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CHECK_FAILED = 2

LEFT, CENTER, RIGHT = "left", "center", "right"


def display_width(text: str) -> int:
    """Approximate terminal/render width of a string.

    Wide East-Asian characters count as 2 columns; zero-width combining marks
    count as 0. Everything else counts as 1. This keeps CJK tables aligned in
    a monospace viewer.
    """
    width = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


def split_row(line: str) -> List[str]:
    """Split a table row on unescaped pipes into trimmed cell strings.

    Leading/trailing pipes are optional. Escaped pipes (\\|) stay literal.
    """
    cells: List[str] = []
    buf: List[str] = []
    escaped = False
    for ch in line:
        if escaped:
            buf.append(ch)
            escaped = False
        elif ch == "\\":
            buf.append(ch)
            escaped = True
        elif ch == "|":
            cells.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    cells.append("".join(buf))

    # Drop the empty cells produced by leading/trailing pipes.
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return [c.strip() for c in cells]


def is_delimiter_row(line: str) -> bool:
    """True if the line is a GFM delimiter row, e.g. | :--- | ---: |."""
    stripped = line.strip()
    if "|" not in stripped and "-" not in stripped:
        return False
    cells = split_row(line)
    if not cells:
        return False
    for cell in cells:
        c = cell.strip()
        if not c:
            return False
        if c[0] == ":":
            c = c[1:]
        if c and c[-1] == ":":
            c = c[:-1]
        if not c or any(ch != "-" for ch in c):
            return False
    return True


def parse_alignment(cell: str) -> str:
    c = cell.strip()
    left = c.startswith(":")
    right = c.endswith(":")
    if left and right:
        return CENTER
    if right:
        return RIGHT
    if left:
        return LEFT
    return LEFT


def looks_like_table_start(lines: List[str], i: int) -> bool:
    """A table is a header line containing a pipe followed by a delimiter row."""
    if i + 1 >= len(lines):
        return False
    header = lines[i]
    if "|" not in header:
        return False
    if is_delimiter_row(header):
        return False
    return is_delimiter_row(lines[i + 1])


def pad_cell(text: str, width: int, align: str) -> str:
    gap = width - display_width(text)
    if gap <= 0:
        return text
    if align == RIGHT:
        return " " * gap + text
    if align == CENTER:
        left = gap // 2
        right = gap - left
        return " " * left + text + " " * right
    return text + " " * gap


def make_delimiter(width: int, align: str) -> str:
    # Minimum dashes so a marker is always visible.
    if align == CENTER:
        return ":" + "-" * max(1, width - 2) + ":"
    if align == RIGHT:
        return "-" * max(1, width - 1) + ":"
    if align == LEFT:
        # Preserve an explicit left marker only if one was given.
        return ":" + "-" * max(1, width - 1)
    return "-" * max(1, width)


def format_table(block: List[str]) -> List[str]:
    """Reformat a list of raw table lines into aligned lines."""
    header = split_row(block[0])
    raw_delims = split_row(block[1])
    body = [split_row(r) for r in block[2:]]

    ncols = max([len(header), len(raw_delims)] + [len(r) for r in body] or [0])

    def fit(row: List[str]) -> List[str]:
        return (row + [""] * ncols)[:ncols]

    header = fit(header)
    body = [fit(r) for r in body]

    aligns = [parse_alignment(c) for c in raw_delims]
    # Track whether the source explicitly marked left alignment, so we can
    # round-trip ":---" rather than silently turning it into "---".
    explicit_left = [c.strip().startswith(":") and not c.strip().endswith(":")
                     for c in raw_delims]
    aligns = (aligns + [LEFT] * ncols)[:ncols]
    explicit_left = (explicit_left + [False] * ncols)[:ncols]

    def min_delim_width(col: int) -> int:
        # Enough room for the alignment marker so the delimiter row never
        # ends up wider than the data columns.
        if aligns[col] == CENTER:
            return 3  # ":-:"
        if aligns[col] == RIGHT:
            return 2  # "-:"
        if aligns[col] == LEFT and explicit_left[col]:
            return 2  # ":-"
        return 1

    widths = [0] * ncols
    for col in range(ncols):
        cells = [header[col]] + [r[col] for r in body]
        widths[col] = max([display_width(c) for c in cells] + [min_delim_width(col)])

    def render(cells: List[str]) -> str:
        out = [pad_cell(cells[c], widths[c], aligns[c]) for c in range(ncols)]
        return "| " + " | ".join(out) + " |"

    lines = [render(header)]

    delim_cells = []
    for c in range(ncols):
        align = aligns[c]
        if align == LEFT and not explicit_left[c]:
            delim_cells.append("-" * widths[c])
        else:
            delim_cells.append(make_delimiter(widths[c], align))
    lines.append("| " + " | ".join(delim_cells) + " |")

    for row in body:
        lines.append(render(row))
    return lines


def process(text: str) -> str:
    lines = text.split("\n")
    # Preserve a trailing newline if present.
    trailing_newline = text.endswith("\n")
    if trailing_newline and lines and lines[-1] == "":
        lines = lines[:-1]

    out: List[str] = []
    i = 0
    n = len(lines)
    while i < n:
        if looks_like_table_start(lines, i):
            block = [lines[i], lines[i + 1]]
            j = i + 2
            while j < n and "|" in lines[j] and lines[j].strip() != "":
                block.append(lines[j])
                j += 1
            out.extend(format_table(block))
            i = j
        else:
            out.append(lines[i])
            i += 1

    result = "\n".join(out)
    if trailing_newline:
        result += "\n"
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mdtable",
        description="Align GitHub-Flavored Markdown tables. Reads stdin or "
                    "files; writes to stdout unless --in-place is given.",
        epilog="Examples:\n"
               "  mdtable README.md                 # print aligned version\n"
               "  mdtable -i README.md docs/*.md    # rewrite files in place\n"
               "  cat notes.md | mdtable            # pipe through\n"
               "  mdtable --check README.md         # exit 2 if not aligned",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("files", nargs="*",
                   help="Markdown files to format (default: read stdin).")
    p.add_argument("-i", "--in-place", action="store_true",
                   help="Rewrite each file in place instead of printing.")
    p.add_argument("-c", "--check", action="store_true",
                   help="Do not write. Exit 2 if any input is not already "
                        "aligned. Useful in CI / pre-commit.")
    p.add_argument("--version", action="version",
                   version="mdtable " + __version__)
    return p


def read_source(path: Optional[str]) -> str:
    if path is None or path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.in_place and not args.files:
        sys.stderr.write("mdtable: --in-place requires at least one file\n")
        return EXIT_ERROR
    if args.in_place and args.check:
        sys.stderr.write("mdtable: choose either --in-place or --check, "
                         "not both\n")
        return EXIT_ERROR

    targets: List[Optional[str]] = args.files if args.files else [None]
    changed_any = False
    had_error = False

    for path in targets:
        try:
            original = read_source(path)
        except FileNotFoundError:
            sys.stderr.write("mdtable: no such file: %s\n" % path)
            had_error = True
            continue
        except OSError as exc:
            sys.stderr.write("mdtable: cannot read %s: %s\n" % (path, exc))
            had_error = True
            continue
        except UnicodeDecodeError:
            sys.stderr.write("mdtable: %s is not valid UTF-8 text\n" % path)
            had_error = True
            continue

        formatted = process(original)
        changed = formatted != original

        if args.check:
            if changed:
                changed_any = True
                name = path if path else "<stdin>"
                sys.stderr.write("would reformat: %s\n" % name)
            continue

        if args.in_place:
            if changed:
                try:
                    with open(path, "w", encoding="utf-8") as fh:
                        fh.write(formatted)
                except OSError as exc:
                    sys.stderr.write("mdtable: cannot write %s: %s\n"
                                     % (path, exc))
                    had_error = True
                    continue
                sys.stderr.write("formatted: %s\n" % path)
        else:
            sys.stdout.write(formatted)

    if had_error:
        return EXIT_ERROR
    if args.check and changed_any:
        return EXIT_CHECK_FAILED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
