#!/usr/bin/env python3
"""diskhog - find what's eating your disk space (stdlib only).

Skeleton: argument parsing only. Core logic added in later commits.
"""
import argparse
import sys

__version__ = "0.1.0"


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
    p.add_argument("--version", action="version",
                   version=f"%(prog)s {__version__}")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    print(f"diskhog: not implemented yet (would scan {args.path!r})",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
