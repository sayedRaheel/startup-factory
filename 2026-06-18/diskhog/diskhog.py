#!/usr/bin/env python3
"""diskhog - find what's eating your disk space (stdlib only).

Scans a directory tree and reports the largest files and/or directories.
"""
import argparse
import os
import sys

__version__ = "0.2.0"

_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]


def human(n: int) -> str:
    """Format a byte count as a human-readable string (base 1024)."""
    size = float(n)
    for unit in _UNITS:
        if size < 1024 or unit == _UNITS[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def parse_size(text: str) -> int:
    """Parse a size like '100M', '1.5G', '512k', '2048' into bytes."""
    text = text.strip()
    if not text:
        raise ValueError("empty size")
    mult = 1
    suffixes = {"B": 1, "K": 1024, "M": 1024**2,
                "G": 1024**3, "T": 1024**4, "P": 1024**5}
    last = text[-1].upper()
    if last in suffixes:
        mult = suffixes[last]
        text = text[:-1]
    return int(float(text) * mult)


def scan(root, follow_symlinks=False):
    """Walk `root` bottom-up, returning (dir_sizes, files).

    dir_sizes maps each directory path to its total recursive byte size.
    files is a list of (size, path) tuples for every regular file seen.
    """
    dir_sizes = {}
    files = []

    def on_error(err):
        print(f"diskhog: warning: {err}", file=sys.stderr)

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
            size = st.st_size
            total += size
            files.append((size, fp))
        for dn in dirnames:
            total += dir_sizes.get(os.path.join(dirpath, dn), 0)
        dir_sizes[dirpath] = total
    return dir_sizes, files


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="diskhog",
        description="Find the largest files and directories under a path, "
                    "and tally reclaimable build/cache directories.",
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
    p.add_argument("--min", dest="min_size", metavar="SIZE", default=None,
                   help="ignore entries smaller than SIZE (e.g. 100M, 1.5G)")
    p.add_argument("-L", "--follow-symlinks", action="store_true",
                   help="follow symlinked directories (off by default)")
    p.add_argument("--version", action="version",
                   version=f"%(prog)s {__version__}")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    min_bytes = parse_size(args.min_size) if args.min_size else 0
    dir_sizes, files = scan(args.path, follow_symlinks=args.follow_symlinks)

    entries = []
    if not args.files_only:
        for d, s in dir_sizes.items():
            if d != os.path.normpath(args.path):
                entries.append((s, d + os.sep, "dir"))
    if not args.dirs_only:
        for s, f in files:
            entries.append((s, f, "file"))

    entries = [e for e in entries if e[0] >= min_bytes]
    entries.sort(key=lambda e: e[0], reverse=True)

    root_total = dir_sizes.get(os.path.normpath(args.path), 0)
    print(f"Total under {args.path!r}: {human(root_total)}")
    print(f"Top {args.top} entries:")
    for size, path, kind in entries[:args.top]:
        tag = "/" if kind == "dir" else " "
        print(f"  {human(size):>10}  {tag} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
