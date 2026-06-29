#!/usr/bin/env python3
"""todotrack - find and report TODO/FIXME-style comments in a codebase.

A single-file, zero-dependency CLI that walks a directory, collects annotation
comments (TODO, FIXME, HACK, etc.), and prints them as text, markdown, json or
csv. Useful for code reviews, tech-debt audits, and CI gates.

Standard library only. Python 3.8+.
"""
from __future__ import annotations

import argparse
import sys

__version__ = "1.0.0"

# Tags scanned by default, in rough priority order (high -> low).
DEFAULT_TAGS = ["FIXME", "BUG", "XXX", "HACK", "TODO", "OPTIMIZE", "NOTE"]

# Directories we never descend into.
DEFAULT_SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "venv", ".venv", "env",
    "__pycache__", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".idea", ".vscode", "target", ".tox", "vendor",
}


def parse_args(argv):
    p = argparse.ArgumentParser(
        prog="todotrack",
        description="Find and report TODO/FIXME-style comments in a codebase.",
        epilog="Example: todotrack src/ --format markdown --fail-on FIXME,BUG",
    )
    p.add_argument("path", nargs="?", default=".",
                   help="file or directory to scan (default: current dir)")
    p.add_argument("-t", "--tags", default=",".join(DEFAULT_TAGS),
                   help="comma-separated tags to search (default: %(default)s)")
    p.add_argument("-f", "--format", choices=["text", "markdown", "json", "csv"],
                   default="text", help="output format (default: text)")
    p.add_argument("--fail-on", default="", metavar="TAGS",
                   help="comma-separated tags that, if found, cause exit code 1")
    p.add_argument("-V", "--version", action="version",
                   version="%(prog)s " + __version__)
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    # Scanning engine is implemented in a later stage.
    print("todotrack %s: scanning not yet implemented" % __version__,
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
