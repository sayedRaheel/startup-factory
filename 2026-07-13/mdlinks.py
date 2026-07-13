#!/usr/bin/env python3
"""mdlinks — offline checker for relative links and heading anchors in Markdown files.

Exit codes: 0 = all links OK, 1 = broken links found, 2 = usage error.
"""

import argparse
import sys

__version__ = "0.1.0"


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="mdlinks",
        description="Offline checker for relative links and heading anchors "
                    "in Markdown files.",
        epilog="Exit codes: 0 = OK, 1 = broken links found, 2 = usage error.")
    parser.add_argument("paths", nargs="*", default=["."],
                        help="files or directories to scan (default: .)")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="print nothing on success")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    print("mdlinks: link checking not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
