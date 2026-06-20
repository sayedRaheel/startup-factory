#!/usr/bin/env python3
"""dupefind - find duplicate files by content (skeleton).

A small, dependency-free CLI that scans one or more directories and reports
groups of files whose contents are byte-for-byte identical.
"""
from __future__ import annotations

import argparse
import sys

__version__ = "0.1.0"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dupefind",
        description="Find duplicate files by content hash (standard library only).",
    )
    p.add_argument("paths", nargs="*", default=["."],
                   help="Directories (or files) to scan. Default: current directory.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # TODO: implement scanning + hashing in next commit
    print(f"dupefind {__version__}: would scan {args.paths}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
