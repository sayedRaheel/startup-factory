#!/usr/bin/env python3
"""mdlinks — offline checker for relative links and heading anchors in Markdown files.

Walks a directory (or takes individual files), extracts links from Markdown,
and verifies that:
  * relative file links point at files/directories that actually exist
  * anchor fragments (#some-heading) match a real heading in the target file

External links (http/https/mailto/...) are ignored by default — this tool is
100% offline and needs no network. Standard library only.

Exit codes: 0 = all links OK, 1 = broken links found, 2 = usage error.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

__version__ = "1.0.0"

MD_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd"}
DEFAULT_EXCLUDES = {".git", "node_modules", ".venv", "venv", "__pycache__",
                    "dist", "build", ".tox", ".mypy_cache", "site-packages"}

# [text](target "title") and ![alt](target) — target captured, <bracketed> allowed
INLINE_LINK_RE = re.compile(
    r"!?\[(?:[^\]\\]|\\.)*\]\(\s*(<[^<>]*>|[^)\s]+)(?:\s+[\"'(][^)]*)?\s*\)"
)
# Reference-style definitions:  [label]: target
REF_DEF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^<>]*>|\S+)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
SETEXT_RE = re.compile(r"^\s{0,3}(=+|-+)\s*$")
HTML_ANCHOR_RE = re.compile(r"<[^>]+\s(?:id|name)\s*=\s*[\"']([^\"']+)[\"']")
CODE_SPAN_RE = re.compile(r"`[^`]*`")
FENCE_RE = re.compile(r"^\s{0,3}(```|~~~)")
EXTERNAL_SCHEMES = ("http:", "https:", "mailto:", "ftp:", "tel:", "data:")

# Characters GitHub strips when slugging a heading (keep word chars, spaces, hyphens)
SLUG_STRIP_RE = re.compile(r"[^\w\- ]", re.UNICODE)
MD_DECOR_RE = re.compile(r"[`*]|__|\[|\]\([^)]*\)")  # light markdown-decoration removal


def github_slug(heading, seen):
    """Approximate GitHub's heading -> anchor slug algorithm."""
    text = MD_DECOR_RE.sub("", heading).strip().lower()
    text = SLUG_STRIP_RE.sub("", text)
    slug = text.replace(" ", "-")
    if slug in seen:
        n = seen[slug]
        seen[slug] = n + 1
        return f"{slug}-{n}"
    seen[slug] = 1
    return slug


def iter_markdown_lines(text):
    """Yield (lineno, line) for lines outside fenced code blocks,
    with inline code spans blanked out."""
    fence = None
    for i, line in enumerate(text.splitlines(), 1):
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            continue
        if fence is not None:
            continue
        yield i, CODE_SPAN_RE.sub("``", line)


def extract_links(text):
    """Return list of (lineno, raw_target) links found in markdown text."""
    links = []
    for lineno, line in iter_markdown_lines(text):
        for m in INLINE_LINK_RE.finditer(line):
            links.append((lineno, m.group(1)))
        m = REF_DEF_RE.match(line)
        if m:
            links.append((lineno, m.group(1)))
    return [(ln, t[1:-1] if t.startswith("<") and t.endswith(">") else t)
            for ln, t in links]


def collect_anchors(text):
    """Return the set of valid anchor slugs for a markdown document."""
    seen = {}
    anchors = set()
    lines = list(iter_markdown_lines(text))
    for idx, (_, line) in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            anchors.add(github_slug(m.group(2), seen))
        elif idx + 1 < len(lines) and SETEXT_RE.match(lines[idx + 1][1]) and line.strip():
            anchors.add(github_slug(line, seen))
        for am in HTML_ANCHOR_RE.finditer(line):
            anchors.add(am.group(1))
    return anchors


class AnchorCache:
    def __init__(self):
        self._cache = {}

    def anchors_for(self, path):
        key = str(path)
        if key not in self._cache:
            try:
                text = Path(path).read_text(encoding="utf-8", errors="replace")
                self._cache[key] = collect_anchors(text)
            except OSError:
                self._cache[key] = set()
        return self._cache[key]


def classify(target):
    """Return 'external', 'anchor', or 'path'."""
    low = target.lower()
    if low.startswith(EXTERNAL_SCHEMES) or low.startswith("//"):
        return "external"
    if target.startswith("#"):
        return "anchor"
    return "path"


def check_file(md_file, root, cache, stats):
    """Check one markdown file; return list of problem dicts."""
    problems = []
    try:
        text = md_file.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [{"file": str(md_file), "line": 0, "link": "",
                 "reason": f"unreadable: {exc}"}]

    own_anchors = None
    for lineno, target in extract_links(text):
        kind = classify(target)
        if kind == "external":
            stats["external"] += 1
            continue
        stats["checked"] += 1

        if kind == "anchor":
            if own_anchors is None:
                own_anchors = collect_anchors(text)
            frag = unquote(target[1:])
            if frag and frag not in own_anchors:
                problems.append({"file": str(md_file), "line": lineno,
                                 "link": target,
                                 "reason": "no such heading anchor in this file"})
            continue

        # path (possibly with #fragment)
        parts = urlsplit(target)
        rel_path = unquote(parts.path)
        frag = unquote(parts.fragment)
        if not rel_path:
            continue
        if rel_path.startswith("/"):
            resolved = (root / rel_path.lstrip("/")).resolve()
        else:
            resolved = (md_file.parent / rel_path).resolve()

        if not resolved.exists():
            problems.append({"file": str(md_file), "line": lineno,
                             "link": target, "reason": "target does not exist"})
            continue
        if frag and resolved.is_file() and resolved.suffix.lower() in MD_EXTENSIONS:
            if frag not in cache.anchors_for(resolved):
                problems.append({"file": str(md_file), "line": lineno,
                                 "link": target,
                                 "reason": f"anchor '#{frag}' not found in target"})
    return problems


def find_markdown_files(paths, excludes):
    files = []
    for p in paths:
        p = Path(p)
        if p.is_file():
            files.append(p.resolve())
        elif p.is_dir():
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = [d for d in dirnames if d not in excludes]
                for name in filenames:
                    if Path(name).suffix.lower() in MD_EXTENSIONS:
                        files.append((Path(dirpath) / name).resolve())
        else:
            raise FileNotFoundError(p)
    return sorted(set(files))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="mdlinks",
        description="Offline checker for relative links and heading anchors "
                    "in Markdown files.",
        epilog="Exit codes: 0 = OK, 1 = broken links found, 2 = usage error.")
    parser.add_argument("paths", nargs="*", default=["."],
                        help="files or directories to scan (default: .)")
    parser.add_argument("--root", default=None,
                        help="directory that absolute links (/like/this.md) "
                             "resolve against (default: first scanned dir)")
    parser.add_argument("--exclude", action="append", default=[],
                        metavar="NAME", help="extra directory name to skip "
                        "(repeatable); .git, node_modules etc. always skipped")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="print nothing on success")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    paths = args.paths or ["."]
    excludes = DEFAULT_EXCLUDES | set(args.exclude)
    try:
        files = find_markdown_files(paths, excludes)
    except FileNotFoundError as exc:
        print(f"mdlinks: error: no such file or directory: {exc}",
              file=sys.stderr)
        return 2

    root_arg = args.root or next((p for p in paths if Path(p).is_dir()), ".")
    root = Path(root_arg).resolve()

    cache = AnchorCache()
    stats = {"checked": 0, "external": 0}
    problems = []
    for md_file in files:
        problems.extend(check_file(md_file, root, cache, stats))

    if args.format == "json":
        print(json.dumps({"files_scanned": len(files),
                          "links_checked": stats["checked"],
                          "external_skipped": stats["external"],
                          "broken": problems}, indent=2))
    else:
        for p in problems:
            print(f"{p['file']}:{p['line']}: BROKEN {p['link']} ({p['reason']})")
        if not args.quiet or problems:
            print(f"mdlinks: {len(files)} file(s), {stats['checked']} link(s) "
                  f"checked, {stats['external']} external skipped, "
                  f"{len(problems)} broken")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
