#!/usr/bin/env python3
"""todotrack - find and report TODO/FIXME-style comments in a codebase.

A single-file, zero-dependency CLI that walks a directory, collects annotation
comments (TODO, FIXME, HACK, etc.), and prints them as text, markdown, json or
csv. Useful for code reviews, tech-debt audits, and CI gates.

Standard library only. Python 3.8+.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import io
import json
import os
import re
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

# Comment leaders that may precede a tag on a line. A tag only counts when one
# of these appears immediately before it (allowing whitespace). This keeps us
# from flagging the word "TODO" inside ordinary strings or identifiers.
# Quote characters are deliberately excluded to avoid matching string literals
# such as `x = 'TODO later'`.
_LEADERS = r"(?:#+|//+|/\*+|\*+|<!--|--|;+|%+)"


def build_pattern(tags):
    """Compile the scanning regex for the given tag list."""
    alt = "|".join(re.escape(t) for t in tags)
    # leader, optional space, TAG, optional (author), optional :/-, message
    return re.compile(
        r"%s[ \t]*(?P<tag>%s)\b[ \t]*(?:\((?P<author>[^)]*)\))?[ \t]*[:\-]?[ \t]*(?P<msg>.*)$"
        % (_LEADERS, alt),
        re.IGNORECASE,
    )


def clean_message(msg):
    """Strip trailing comment terminators and whitespace from a message."""
    msg = msg.rstrip()
    for term in ("-->", "*/", "*", "#"):
        if msg.endswith(term):
            msg = msg[: -len(term)].rstrip()
    return msg


def is_probably_binary(path, sniff=2048):
    """Cheap binary check: NUL byte in the first chunk means skip."""
    try:
        with open(path, "rb") as fh:
            return b"\x00" in fh.read(sniff)
    except OSError:
        return True


def iter_files(root, skip_dirs, exclude_globs, follow_symlinks=False):
    """Yield candidate file paths under root, honoring skip rules."""
    if os.path.isfile(root):
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            if any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(name, g)
                   for g in exclude_globs):
                continue
            yield full


def scan_file(path, pattern, display_path):
    """Return a list of hit dicts for one file."""
    hits = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                m = pattern.search(line)
                if not m:
                    continue
                hits.append({
                    "file": display_path,
                    "line": lineno,
                    "tag": m.group("tag").upper(),
                    "author": (m.group("author") or "").strip(),
                    "message": clean_message(m.group("msg")),
                })
    except OSError as exc:
        print("todotrack: cannot read %s: %s" % (display_path, exc),
              file=sys.stderr)
    return hits


def collect(root, tags, skip_dirs, exclude_globs, follow_symlinks):
    pattern = build_pattern(tags)
    results = []
    for path in iter_files(root, skip_dirs, exclude_globs, follow_symlinks):
        if is_probably_binary(path):
            continue
        display = os.path.relpath(path, root) if os.path.isdir(root) else path
        results.extend(scan_file(path, pattern, display))
    return results


# ----------------------------- output formats ------------------------------ #

def render_text(hits, tags, use_color):
    if not hits:
        return "No matching comments found.\n"
    def color(s, code):
        return "\033[%sm%s\033[0m" % (code, s) if use_color else s
    order = {t: i for i, t in enumerate(tags)}
    hits = sorted(hits, key=lambda h: (order.get(h["tag"], 99), h["file"], h["line"]))
    out = io.StringIO()
    current = None
    for h in hits:
        if h["tag"] != current:
            current = h["tag"]
            out.write("\n%s\n" % color(current, "1;33"))
        loc = "%s:%d" % (h["file"], h["line"])
        who = " (%s)" % h["author"] if h["author"] else ""
        msg = h["message"] or "(no description)"
        out.write("  %s%s  %s\n" % (color(loc, "36"), who, msg))
    return out.getvalue()


def render_markdown(hits, tags):
    out = io.StringIO()
    out.write("# TODO report\n\n")
    if not hits:
        out.write("No matching comments found.\n")
        return out.getvalue()
    out.write("| Tag | Location | Author | Message |\n")
    out.write("| --- | --- | --- | --- |\n")
    order = {t: i for i, t in enumerate(tags)}
    for h in sorted(hits, key=lambda h: (order.get(h["tag"], 99), h["file"], h["line"])):
        loc = "%s:%d" % (h["file"], h["line"])
        msg = (h["message"] or "").replace("|", "\\|")
        out.write("| %s | %s | %s | %s |\n" % (h["tag"], loc, h["author"], msg))
    return out.getvalue()


def render_json(hits):
    return json.dumps(hits, indent=2) + "\n"


def render_csv(hits):
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=["tag", "file", "line", "author", "message"])
    w.writeheader()
    for h in hits:
        w.writerow({k: h[k] for k in ("tag", "file", "line", "author", "message")})
    return out.getvalue()


def summarize(hits, tags):
    counts = {}
    for h in hits:
        counts[h["tag"]] = counts.get(h["tag"], 0) + 1
    parts = ["%s=%d" % (t, counts[t]) for t in tags if t in counts]
    return "Total: %d  (%s)" % (len(hits), ", ".join(parts) if parts else "none")


# --------------------------------- cli -------------------------------------- #

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
    p.add_argument("-e", "--exclude", action="append", default=[], metavar="GLOB",
                   help="glob of files to skip; repeatable (e.g. -e '*.min.js')")
    p.add_argument("--fail-on", default="", metavar="TAGS",
                   help="comma-separated tags that, if found, cause exit code 1")
    p.add_argument("--no-color", action="store_true",
                   help="disable ANSI color in text output")
    p.add_argument("--follow-symlinks", action="store_true",
                   help="follow symlinked directories while walking")
    p.add_argument("--no-summary", action="store_true",
                   help="suppress the trailing summary line (text format)")
    p.add_argument("-o", "--output", metavar="FILE",
                   help="write report to FILE instead of stdout")
    p.add_argument("-V", "--version", action="version",
                   version="%(prog)s " + __version__)
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if not os.path.exists(args.path):
        print("todotrack: path not found: %s" % args.path, file=sys.stderr)
        return 2

    tags = [t.strip().upper() for t in args.tags.split(",") if t.strip()]
    if not tags:
        print("todotrack: no tags to search for", file=sys.stderr)
        return 2

    hits = collect(args.path, tags, DEFAULT_SKIP_DIRS, args.exclude,
                   args.follow_symlinks)

    if args.format == "text":
        use_color = not args.no_color and (
            args.output is None and sys.stdout.isatty())
        body = render_text(hits, tags, use_color)
        if not args.no_summary:
            body += "\n" + summarize(hits, tags) + "\n"
    elif args.format == "markdown":
        body = render_markdown(hits, tags)
    elif args.format == "json":
        body = render_json(hits)
    else:
        body = render_csv(hits)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(body)
        except OSError as exc:
            print("todotrack: cannot write %s: %s" % (args.output, exc),
                  file=sys.stderr)
            return 2
    else:
        sys.stdout.write(body)

    fail_tags = {t.strip().upper() for t in args.fail_on.split(",") if t.strip()}
    if fail_tags and any(h["tag"] in fail_tags for h in hits):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
