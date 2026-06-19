#!/usr/bin/env python3
"""logscrub - redact secrets and PII from logs/text before sharing.

Standard library only. See README.md for details.
"""
import argparse
import sys

__version__ = "0.1.0"


def build_parser():
    p = argparse.ArgumentParser(
        prog="logscrub",
        description="Redact secrets and PII (API keys, tokens, emails, IPs, ...) "
                    "from logs before pasting them into issues, chat, or Stack Overflow.",
        epilog="Examples:\n"
               "  cat app.log | logscrub\n"
               "  logscrub app.log -o clean.log\n"
               "  logscrub app.log --only aws_key,jwt --stats\n"
               "  logscrub --list-types",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("files", nargs="*",
                   help="Input file(s). If omitted, reads from stdin.")
    p.add_argument("-o", "--output",
                   help="Write result to this file instead of stdout.")
    p.add_argument("-i", "--in-place", action="store_true",
                   help="Edit the given file(s) in place.")
    p.add_argument("--only", metavar="TYPES",
                   help="Comma-separated list of detector types to apply (others skipped).")
    p.add_argument("--skip", metavar="TYPES",
                   help="Comma-separated list of detector types to skip.")
    p.add_argument("--mask", default="[REDACTED:{type}]",
                   help="Replacement template. '{type}' is filled in. Default: '[REDACTED:{type}]'.")
    p.add_argument("--stats", action="store_true",
                   help="Print a per-type redaction count summary to stderr.")
    p.add_argument("--list-types", action="store_true",
                   help="List available detector types and exit.")
    p.add_argument("--version", action="version", version="%(prog)s " + __version__)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    # Implemented in later commits.
    parser.error("not implemented yet")


if __name__ == "__main__":
    main()
