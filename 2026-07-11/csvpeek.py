#!/usr/bin/env python3
"""csvpeek — quickly inspect a CSV that's too big for Excel.

Streams the file (constant memory), so a 10 GB CSV is fine.
Standard library only. Python 3.8+.

Examples:
    csvpeek.py data.csv                 # summary + first 10 rows
    csvpeek.py data.csv --head 25       # show more rows
    csvpeek.py data.csv --cols          # just list the columns
    csvpeek.py data.csv --stats         # per-column type/stats scan
    cat data.csv | csvpeek.py -         # read from stdin
"""

import argparse
import csv
import io
import math
import sys

MAX_CELL_WIDTH = 32
DISTINCT_CAP = 10000  # stop counting distincts past this, report "10000+"


def sniff_dialect(sample: str, delimiter: str = None):
    """Return (delimiter, has_header) using csv.Sniffer with safe fallbacks."""
    sniffer = csv.Sniffer()
    if delimiter is None:
        try:
            delimiter = sniffer.sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    try:
        has_header = sniffer.has_header(sample)
    except csv.Error:
        has_header = True
    return delimiter, has_header


def truncate(s: str, width: int = MAX_CELL_WIDTH) -> str:
    s = s.replace("\n", "\\n").replace("\r", "")
    return s if len(s) <= width else s[: width - 1] + "…"


def render_table(header, rows):
    """Render rows as an aligned text table."""
    if not rows and not header:
        return "(no rows)"
    ncols = max([len(header)] + [len(r) for r in rows]) if (header or rows) else 0
    widths = [0] * ncols
    all_rows = ([header] if header else []) + rows
    cells = [[truncate(r[i]) if i < len(r) else "" for i in range(ncols)] for r in all_rows]
    for row in cells:
        for i, c in enumerate(row):
            widths[i] = max(widths[i], len(c))
    lines = []
    for idx, row in enumerate(cells):
        lines.append("  ".join(c.ljust(widths[i]) for i, c in enumerate(row)).rstrip())
        if header and idx == 0:
            lines.append("  ".join("-" * widths[i] for i in range(ncols)))
    return "\n".join(lines)


def classify(value: str):
    """Classify a cell as int, float, or str (empty returns None)."""
    v = value.strip()
    if v == "":
        return None, None
    try:
        return "int", int(v)
    except ValueError:
        pass
    try:
        f = float(v)
        if math.isfinite(f):
            return "float", f
    except ValueError:
        pass
    return "str", v


class ColStat:
    __slots__ = ("nonnull", "types", "minv", "maxv", "total", "numcount", "distinct", "capped")

    def __init__(self):
        self.nonnull = 0
        self.types = set()
        self.minv = None
        self.maxv = None
        self.total = 0.0
        self.numcount = 0
        self.distinct = set()
        self.capped = False

    def feed(self, raw: str):
        t, v = classify(raw)
        if t is None:
            return
        self.nonnull += 1
        self.types.add(t)
        if not self.capped:
            self.distinct.add(raw)
            if len(self.distinct) > DISTINCT_CAP:
                self.capped = True
                self.distinct.clear()
        if t in ("int", "float"):
            self.numcount += 1
            self.total += v
            self.minv = v if self.minv is None or v < self.minv else self.minv
            self.maxv = v if self.maxv is None or v > self.maxv else self.maxv

    @property
    def kind(self):
        if not self.types:
            return "empty"
        if self.types <= {"int"}:
            return "int"
        if self.types <= {"int", "float"}:
            return "float"
        return "mixed" if len(self.types) > 1 else "str"


def open_input(path):
    if path == "-":
        return io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace", newline="")
    return open(path, "r", encoding="utf-8", errors="replace", newline="")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="csvpeek",
        description="Peek at a CSV file without loading it into Excel or pandas. "
        "Streams the file, so arbitrarily large inputs are fine.",
    )
    p.add_argument("file", help="CSV file to inspect, or '-' for stdin")
    p.add_argument("-n", "--head", type=int, default=10, metavar="N",
                   help="number of data rows to preview (default: 10)")
    p.add_argument("-d", "--delimiter", default=None,
                   help="field delimiter (default: auto-detect among , ; tab |)")
    p.add_argument("--no-header", action="store_true",
                   help="treat the first row as data, not column names")
    p.add_argument("--cols", action="store_true",
                   help="only list column names (with index) and exit")
    p.add_argument("--stats", action="store_true",
                   help="full scan: per-column type, non-null %%, distinct count, min/max/mean")
    args = p.parse_args(argv)

    if args.head < 0:
        print("error: --head must be >= 0", file=sys.stderr)
        return 2

    try:
        fh = open_input(args.file)
    except OSError as e:
        print(f"error: cannot open {args.file!r}: {e.strerror or e}", file=sys.stderr)
        return 1

    with fh:
        sample = fh.read(64 * 1024)
        if not sample.strip():
            print("error: input is empty", file=sys.stderr)
            return 1
        delimiter, sniffed_header = sniff_dialect(sample, args.delimiter)
        has_header = not args.no_header and sniffed_header

        if args.file == "-":
            # stdin can't seek: replay the sample, then continue with the rest
            stream = io.StringIO(sample)
            reader = csv.reader(_chain_lines(stream, fh), delimiter=delimiter)
        else:
            fh.seek(0)
            reader = csv.reader(fh, delimiter=delimiter)

        try:
            first = next(reader)
        except StopIteration:
            print("error: input is empty", file=sys.stderr)
            return 1
        except csv.Error as e:
            print(f"error: cannot parse CSV: {e}", file=sys.stderr)
            return 1

        if has_header:
            header = first
        else:
            header = [f"col{i}" for i in range(len(first))]

        if args.cols:
            for i, name in enumerate(header):
                print(f"{i}\t{name}")
            return 0

        head_rows = [] if has_header else [first]
        stats = [ColStat() for _ in header] if args.stats else None
        if stats and not has_header:
            _feed(stats, first)

        nrows = 0 if has_header else 1
        ragged = 0
        try:
            for row in reader:
                nrows += 1
                if len(row) != len(header):
                    ragged += 1
                if len(head_rows) < args.head:
                    head_rows.append(row)
                elif not args.stats:
                    # no full scan requested: keep reading only to count rows
                    pass
                if stats:
                    _feed(stats, row)
        except csv.Error as e:
            print(f"warning: parse error after row {nrows}: {e}", file=sys.stderr)

        delim_name = {",": "comma", ";": "semicolon", "\t": "tab", "|": "pipe"}.get(delimiter, repr(delimiter))
        print(f"file:      {args.file}")
        print(f"delimiter: {delim_name}")
        print(f"header:    {'yes' if has_header else 'no (synthetic col0..colN)'}")
        print(f"columns:   {len(header)}")
        print(f"rows:      {nrows:,}" + (f"  ({ragged:,} ragged)" if ragged else ""))
        print()
        print(render_table(header, head_rows))
        if nrows > len(head_rows):
            print(f"… {nrows - len(head_rows):,} more rows")

        if stats:
            print()
            srows = []
            for name, st in zip(header, stats):
                pct = f"{100.0 * st.nonnull / nrows:.0f}%" if nrows else "0%"
                dis = f"{DISTINCT_CAP}+" if st.capped else str(len(st.distinct))
                if st.numcount and st.kind in ("int", "float"):
                    mean = st.total / st.numcount
                    mn, mx, mean_s = str(st.minv), str(st.maxv), f"{mean:.4g}"
                else:
                    mn = mx = mean_s = ""
                srows.append([name, st.kind, pct, dis, mn, mx, mean_s])
            print(render_table(["column", "type", "non-null", "distinct", "min", "max", "mean"], srows))
    return 0


def _feed(stats, row):
    for i, cell in enumerate(row):
        if i < len(stats):
            stats[i].feed(cell)


def _chain_lines(first, second):
    for line in first:
        yield line
    for line in second:
        yield line


if __name__ == "__main__":
    sys.exit(main())
