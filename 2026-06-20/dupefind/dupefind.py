#!/usr/bin/env python3
"""dupefind - find duplicate files by content.

A small, dependency-free CLI that scans one or more directories and reports
groups of files whose contents are byte-for-byte identical. It is careful to
do as little work as possible: files are first grouped by size, then by a
quick hash of their leading bytes, and only then by a full content hash. This
avoids reading large files in full unless they are genuine duplicate
candidates.

Standard library only. No third-party dependencies.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys

__version__ = "1.0.0"

# Number of leading bytes used for the cheap "partial" hash pass.
_PARTIAL_BYTES = 65536
# Chunk size for streaming full-file hashing.
_CHUNK = 1024 * 1024


def human_size(n: int) -> str:
    """Return a human-readable byte size, e.g. 1536 -> '1.5 KB'."""
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(n)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


def iter_files(paths, follow_symlinks=False, include_hidden=False):
    """Yield regular files under the given paths (recursively for dirs)."""
    for path in paths:
        if os.path.isfile(path):
            yield path
            continue
        if not os.path.isdir(path):
            print(f"dupefind: warning: not found, skipping: {path}",
                  file=sys.stderr)
            continue
        for root, dirs, files in os.walk(path, followlinks=follow_symlinks):
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith(".")]
            for name in files:
                if not include_hidden and name.startswith("."):
                    continue
                full = os.path.join(root, name)
                if os.path.islink(full) and not follow_symlinks:
                    continue
                if os.path.isfile(full):
                    yield full


def _hash_file(path, limit=None):
    """Return a sha256 hex digest of a file, optionally only the first `limit`
    bytes. Returns None if the file cannot be read."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            if limit is not None:
                h.update(f.read(limit))
            else:
                while True:
                    chunk = f.read(_CHUNK)
                    if not chunk:
                        break
                    h.update(chunk)
    except OSError as exc:
        print(f"dupefind: warning: cannot read {path}: {exc}", file=sys.stderr)
        return None
    return h.hexdigest()


def _group_by(items, keyfunc):
    """Group items into {key: [items]}, dropping unkeyable (None) items."""
    groups = {}
    for item in items:
        key = keyfunc(item)
        if key is None:
            continue
        groups.setdefault(key, []).append(item)
    return groups


def find_duplicates(files, min_size=1):
    """Return a list of duplicate groups. Each group is (size, [paths...])
    where every path has identical content. Groups are sorted by the total
    wasted space (largest first)."""
    # Pass 1: group by size (cheap, no reads).
    sized = {}
    for path in files:
        try:
            size = os.path.getsize(path)
        except OSError as exc:
            print(f"dupefind: warning: cannot stat {path}: {exc}",
                  file=sys.stderr)
            continue
        if size < min_size:
            continue
        sized.setdefault(size, []).append(path)

    candidate_groups = []
    for size, paths in sized.items():
        if len(paths) < 2:
            continue
        # Pass 2: group by partial hash (read only leading bytes).
        for _, part in _group_by(
            paths, lambda p: _hash_file(p, limit=_PARTIAL_BYTES)
        ).items():
            if len(part) < 2:
                continue
            # Pass 3: confirm by full hash.
            for _, full in _group_by(part, _hash_file).items():
                if len(full) >= 2:
                    candidate_groups.append((size, sorted(full)))

    # Sort by wasted space: size * (count - 1), largest first.
    candidate_groups.sort(key=lambda g: g[0] * (len(g[1]) - 1), reverse=True)
    return candidate_groups


def build_parser():
    p = argparse.ArgumentParser(
        prog="dupefind",
        description="Find duplicate files by content (standard library only).",
        epilog="Exit codes: 0=no duplicates, 1=duplicates found, 2=usage error.",
    )
    p.add_argument("paths", nargs="*", default=["."],
                   help="Directories or files to scan. Default: current dir.")
    p.add_argument("-m", "--min-size", type=int, default=1, metavar="BYTES",
                   help="Ignore files smaller than BYTES (default: 1).")
    p.add_argument("-H", "--hidden", action="store_true",
                   help="Include hidden files and directories.")
    p.add_argument("-L", "--follow-symlinks", action="store_true",
                   help="Follow symbolic links (off by default).")
    p.add_argument("--json", action="store_true",
                   help="Emit results as JSON instead of text.")
    p.add_argument("-q", "--quiet", action="store_true",
                   help="Only print the summary line.")
    p.add_argument("--version", action="version",
                   version=f"%(prog)s {__version__}")
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.min_size < 0:
        parser.error("--min-size must be >= 0")

    files = iter_files(args.paths, follow_symlinks=args.follow_symlinks,
                       include_hidden=args.hidden)
    groups = find_duplicates(files, min_size=max(args.min_size, 0))

    wasted = sum(size * (len(paths) - 1) for size, paths in groups)

    if args.json:
        import json
        payload = {
            "duplicate_groups": [
                {"size": size, "wasted_bytes": size * (len(paths) - 1),
                 "files": paths}
                for size, paths in groups
            ],
            "group_count": len(groups),
            "wasted_bytes": wasted,
        }
        print(json.dumps(payload, indent=2))
        return 1 if groups else 0

    if not args.quiet:
        for size, paths in groups:
            print(f"# {len(paths)} files, {human_size(size)} each "
                  f"({human_size(size * (len(paths) - 1))} reclaimable)")
            for p in paths:
                print(f"  {p}")
            print()

    if groups:
        print(f"Found {len(groups)} duplicate group(s); "
              f"{human_size(wasted)} reclaimable.")
        return 1
    print("No duplicate files found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
