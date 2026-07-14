#!/usr/bin/env python3
"""ghostchars \u2014 find invisible and confusable Unicode characters in source files.

You copied code from a website, a PDF, Slack, or Word, and now the compiler
says `SyntaxError: invalid character '"'` or something equally cryptic \u2014 but
the code *looks* fine. The culprit is almost always an invisible character
(zero-width space, BOM, bidi control) or a confusable one (smart quotes,
en-dashes, non-breaking spaces). ghostchars finds them, points at the exact
line and column, and can fix them for you.

Standard library only. Python 3.8+.

Exit codes:
  0  no offending characters found
  1  offending characters found (or fixed with --fix)
  2  usage / IO error
"""

import argparse
import sys
import unicodedata
from pathlib import Path

__version__ = "1.0.0"

# Characters that should be stripped entirely: they are invisible and never
# belong in source code.
STRIP = {
    "\u200B": "ZERO WIDTH SPACE",
    "\u200C": "ZERO WIDTH NON-JOINER",
    "\u200D": "ZERO WIDTH JOINER",
    "\u2060": "WORD JOINER",
    "\uFEFF": "ZERO WIDTH NO-BREAK SPACE (BOM)",
    "\u00AD": "SOFT HYPHEN",
    "\u180E": "MONGOLIAN VOWEL SEPARATOR",
    # Bidirectional control characters -- also a security concern
    # (see "Trojan Source", CVE-2021-42574).
    "\u200E": "LEFT-TO-RIGHT MARK",
    "\u200F": "RIGHT-TO-LEFT MARK",
    "\u202A": "LEFT-TO-RIGHT EMBEDDING",
    "\u202B": "RIGHT-TO-LEFT EMBEDDING",
    "\u202C": "POP DIRECTIONAL FORMATTING",
    "\u202D": "LEFT-TO-RIGHT OVERRIDE",
    "\u202E": "RIGHT-TO-LEFT OVERRIDE",
    "\u2066": "LEFT-TO-RIGHT ISOLATE",
    "\u2067": "RIGHT-TO-LEFT ISOLATE",
    "\u2068": "FIRST STRONG ISOLATE",
    "\u2069": "POP DIRECTIONAL ISOLATE",
}

# Characters that look like plain ASCII but aren't: replaced with the ASCII
# equivalent shown.
REPLACE = {
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201A": "'",   # single low-9 quote
    "\u201B": "'",   # single high-reversed-9 quote
    "\u2032": "'",   # prime
    "\u201C": '"',   # left double quote
    "\u201D": '"',   # right double quote
    "\u201E": '"',   # double low-9 quote
    "\u2033": '"',   # double prime
    "\u2013": "-",   # en dash
    "\u2014": "-",   # em dash
    "\u2212": "-",   # minus sign
    "\u2010": "-",   # hyphen
    "\u2011": "-",   # non-breaking hyphen
    "\u00A0": " ",   # no-break space
    "\u2002": " ",   # en space
    "\u2003": " ",   # em space
    "\u2007": " ",   # figure space
    "\u2009": " ",   # thin space
    "\u200A": " ",   # hair space
    "\u202F": " ",   # narrow no-break space
    "\u205F": " ",   # medium mathematical space
    "\u3000": " ",   # ideographic space
    "\u2026": "...",  # horizontal ellipsis
    "\u2028": "\n",  # line separator
    "\u2029": "\n",  # paragraph separator
}


def char_name(ch):
    """Best-effort Unicode name for a character."""
    try:
        return unicodedata.name(ch)
    except ValueError:
        return STRIP.get(ch, "UNKNOWN")


def scan_text(text):
    """Scan text and return a list of findings.

    Each finding is a dict: line (1-based), col (1-based), char, codepoint,
    name, action ('strip' or 'replace'), replacement.
    """
    findings = []
    # splitlines() would also split on U+2028/U+2029, hiding their location,
    # so split manually on \n only.
    for lineno, line in enumerate(text.split("\n"), start=1):
        for col, ch in enumerate(line, start=1):
            if ch in STRIP:
                findings.append({
                    "line": lineno, "col": col, "char": ch,
                    "codepoint": f"U+{ord(ch):04X}",
                    "name": char_name(ch),
                    "action": "strip", "replacement": "",
                })
            elif ch in REPLACE:
                findings.append({
                    "line": lineno, "col": col, "char": ch,
                    "codepoint": f"U+{ord(ch):04X}",
                    "name": char_name(ch),
                    "action": "replace", "replacement": REPLACE[ch],
                })
    return findings


def format_findings(path_label, text, findings, show_context=True):
    """Human-readable report for one file's findings."""
    out = []
    lines = text.split("\n")
    for f in findings:
        what = ("strip" if f["action"] == "strip"
                else f"replace with {f['replacement']!r}")
        out.append(f"{path_label}:{f['line']}:{f['col']}: "
                   f"{f['codepoint']} {f['name']}  [{what}]")
        if show_context:
            src = lines[f["line"] - 1]
            # Render invisibles as a visible placeholder so the caret lands
            # on something.
            rendered = "".join("␀" if c in STRIP else c for c in src)
            out.append("    " + rendered)
            out.append("    " + " " * (f["col"] - 1) + "^")
    return "\n".join(out)


def fix_text(text):
    """Return text with all offending characters stripped or replaced."""
    out = []
    for ch in text:
        if ch in STRIP:
            continue
        out.append(REPLACE.get(ch, ch))
    return "".join(out)


def read_source(path):
    """Read a file as UTF-8 text. Returns (text, None) or (None, error)."""
    try:
        data = Path(path).read_bytes()
    except OSError as e:
        return None, str(e)
    if b"\x00" in data:
        return None, "binary file (contains NUL bytes), skipped"
    try:
        return data.decode("utf-8"), None
    except UnicodeDecodeError as e:
        return None, f"not valid UTF-8 ({e}), skipped"


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="ghostchars",
        description="Find (and fix) invisible/confusable Unicode characters "
                    "in source files \u2014 the ones that sneak in when you copy "
                    "code from websites, PDFs, Word, or chat apps.",
        epilog="Examples:\n"
               "  ghostchars app.py                 # report offenders\n"
               "  ghostchars src/*.js --json        # machine-readable\n"
               "  cat snippet.py | ghostchars -     # scan stdin\n"
               "  ghostchars app.py --fix           # fix in place (.bak kept)\n"
               "  pbpaste | ghostchars - --fix      # clean clipboard code\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("files", nargs="+",
                    help="files to scan, or '-' for stdin")
    ap.add_argument("--fix", action="store_true",
                    help="repair files in place (keeps a .bak backup); "
                         "with '-', write fixed text to stdout")
    ap.add_argument("--no-backup", action="store_true",
                    help="with --fix, don't keep .bak backups")
    ap.add_argument("--json", action="store_true",
                    help="output findings as JSON")
    ap.add_argument("-q", "--quiet", action="store_true",
                    help="no output, just the exit code")
    ap.add_argument("--no-context", action="store_true",
                    help="omit source-line context in the report")
    ap.add_argument("--version", action="version",
                    version=f"%(prog)s {__version__}")
    args = ap.parse_args(argv)

    all_findings = {}
    had_error = False

    for path in args.files:
        if path == "-":
            text = sys.stdin.read()
            label = "<stdin>"
        else:
            text, err = read_source(path)
            label = path
            if err is not None:
                print(f"ghostchars: {path}: {err}", file=sys.stderr)
                had_error = True
                continue
        findings = scan_text(text)

        if args.fix:
            fixed = fix_text(text)
            if path == "-":
                sys.stdout.write(fixed)
            elif findings:
                p = Path(path)
                if not args.no_backup:
                    p.with_suffix(p.suffix + ".bak").write_bytes(
                        p.read_bytes())
                p.write_text(fixed, encoding="utf-8")
                if not args.quiet and not args.json:
                    print(f"fixed {path}: {len(findings)} character(s) "
                          f"repaired"
                          + ("" if args.no_backup else f" (backup: {p}.bak)"),
                          file=sys.stderr)

        if findings:
            all_findings[label] = (text, findings)

    if args.json:
        import json as _json
        payload = {label: fs for label, (_, fs) in all_findings.items()}
        # char itself is not JSON-friendly to eyeball; drop it
        for fs in payload.values():
            for f in fs:
                f.pop("char", None)
        print(_json.dumps(payload, indent=2))
    elif not args.quiet and not args.fix:
        for label, (text, findings) in all_findings.items():
            print(format_findings(label, text, findings,
                                  show_context=not args.no_context))
        total = sum(len(fs) for _, fs in all_findings.values())
        if total:
            print(f"\n{total} suspicious character(s) in "
                  f"{len(all_findings)} file(s).")
        else:
            print("Clean: no invisible or confusable characters found.")

    if had_error:
        return 2
    return 1 if all_findings else 0


if __name__ == "__main__":
    sys.exit(main())
