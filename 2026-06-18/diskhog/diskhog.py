#!/usr/bin/env python3
"""diskhog - find what's eating your disk space (stdlib only).

Scans a directory tree and reports the largest files and/or directories,
or (with --reclaim) tallies common build/cache directories you can safely
delete to free space.

No third-party dependencies. Python 3.8+.
"""
import argparse
import json
import os
import sys

__version__ = "1.0.0"

_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]

# Directory names that are typically regenerable and safe-ish to delete.
RECLAIMABLE = {
    "node_modules", "__pycache__", ".venv", "venv", "env",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    "target", "build", "dist", ".next", ".nuxt", ".gradle",
    ".terraform", "vendor", ".cache", "DerivedData", ".parcel-cache",
}


def human(n: int) -> str:
    """Format a byte count as a human-readable string (base 1024)."""
    size = float(n)
    for unit in _UNITS:
        if size < 1024 or unit == _UNITS[-1]:
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def parse_size(text: str) -> int:
    """Parse a size like '100M', '1.5G', '512k', '2048' into bytes."""
    text = text.strip()
    if not text:
        raise ValueError("empty size value")
    suffixes = {"B": 1, "K": 1024, "M": 1024**2,
                "G": 1024**3, "T": 1024**4, "P": 1024**5}
    last = text[-1].upper()
    mult = 1
    if last in suffixes:
        mult = suffixes[last]
        text = text[:-1]
    try:
        return int(float(text) * mult)
    except ValueError:
        raise ValueError(f"invalid size: {text!r}")


def scan(root, follow_symlinks=False, warn=None):
    """Walk `root` bottom-up, returning (dir_sizes, files).

    dir_sizes maps each directory path to its total recursive byte size.
    files is a list of (size, path) tuples for every regular file seen.
    """
    dir_sizes = {}
    files = []

    def on_error(err):
        if warn:
            warn(f"warning: {err}")

    for dirpath, dirnames, filenames in os.walk(
        root, topdown=False, onerror=on_error, followlinks=follow_symlinks
    ):
        total = 0
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            try:
                st = os.lstat(fp)
            except OSError:
                continue
            total += st.st_size
            files.append((st.st_size, fp))
        for dn in dirnames:
            total += dir_sizes.get(os.path.join(dirpath, dn), 0)
        dir_sizes[dirpath] = total
    return dir_sizes, files


def find_reclaimable(dir_sizes):
    """Return outermost reclaimable dirs as (size, path), no nested duplicates."""
    matches = [d for d in dir_sizes if os.path.basename(d) in RECLAIMABLE]
    matches.sort(key=len)  # shorter paths (outermost) first
    kept = []
    for d in matches:
        if any(d == k or d.startswith(k + os.sep) for k in kept):
            continue  # nested inside an already-counted reclaimable dir
        kept.append(d)
    result = [(dir_sizes[d], d) for d in kept]
    result.sort(reverse=True)
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="diskhog",
        description="Find the largest files and directories under a path, "
                    "and tally reclaimable build/cache directories.",
        epilog="Examples:\n"
               "  diskhog ~/projects -n 15\n"
               "  diskhog . --reclaim\n"
               "  diskhog /var/log --files-only --min 50M",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("path", nargs="?", default=".",
                   help="directory to scan (default: current directory)")
    p.add_argument("-n", "--top", type=int, default=20,
                   help="show the N largest entries (default: 20)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--files-only", action="store_true",
                   help="only rank individual files")
    g.add_argument("--dirs-only", action="store_true",
                   help="only rank directories")
    p.add_argument("--reclaim", action="store_true",
                   help="instead of ranking, list reclaimable build/cache dirs")
    p.add_argument("--min", dest="min_size", metavar="SIZE", default=None,
                   help="ignore entries smaller than SIZE (e.g. 100M, 1.5G)")
    p.add_argument("-L", "--follow-symlinks", action="store_true",
                   help="follow symlinked directories (off by default)")
    p.add_argument("--json", action="store_true",
                   help="emit machine-readable JSON")
    p.add_argument("--version", action="version",
                   version=f"%(prog)s {__version__}")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    def warn(msg):
        print(f"diskhog: {msg}", file=sys.stderr)

    if not os.path.exists(args.path):
        warn(f"error: no such path: {args.path!r}")
        return 1
    if not os.path.isdir(args.path):
        warn(f"error: not a directory: {args.path!r}")
        return 1

    try:
        min_bytes = parse_size(args.min_size) if args.min_size else 0
    except ValueError as e:
        warn(f"error: {e}")
        return 2

    root = os.path.normpath(args.path)
    dir_sizes, files = scan(args.path,
                            follow_symlinks=args.follow_symlinks, warn=warn)
    root_total = dir_sizes.get(root, 0)

    if args.reclaim:
        rec = [(s, p) for s, p in find_reclaimable(dir_sizes) if s >= min_bytes]
        recoverable = sum(s for s, _ in rec)
        if args.json:
            print(json.dumps({
                "path": args.path,
                "reclaimable_bytes": recoverable,
                "items": [{"bytes": s, "path": p} for s, p in rec],
            }, indent=2))
            return 0
        if not rec:
            print(f"No reclaimable build/cache directories found under "
                  f"{args.path!r}.")
            return 0
        print(f"Reclaimable build/cache directories under {args.path!r}:")
        for size, path in rec:
            print(f"  {human(size):>10}   {path}{os.sep}")
        print(f"\nTotal reclaimable: {human(recoverable)}")
        print("Review first, then e.g.:")
        print("  diskhog --reclaim --json . | "
              "python3 -c \"import sys,json;"
              "[print(i['path']) for i in json.load(sys.stdin)['items']]\"")
        return 0

    entries = []
    if not args.files_only:
        for d, s in dir_sizes.items():
            if d != root:
                entries.append((s, d, "dir"))
    if not args.dirs_only:
        for s, f in files:
            entries.append((s, f, "file"))
    entries = [e for e in entries if e[0] >= min_bytes]
    entries.sort(key=lambda e: e[0], reverse=True)
    top = entries[:args.top]

    if args.json:
        print(json.dumps({
            "path": args.path,
            "total_bytes": root_total,
            "entries": [{"bytes": s, "path": p, "type": k} for s, p, k in top],
        }, indent=2))
        return 0

    print(f"Total under {args.path!r}: {human(root_total)}")
    if not top:
        print("No entries matched.")
        return 0
    print(f"Top {min(args.top, len(top))} entries:")
    for size, path, kind in top:
        suffix = os.sep if kind == "dir" else ""
        tag = "d" if kind == "dir" else "f"
        print(f"  {human(size):>10}  [{tag}] {path}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
