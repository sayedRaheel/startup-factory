#!/usr/bin/env python3
"""logscrub - redact secrets and PII from logs/text before sharing.

A tiny, zero-dependency CLI that scans text for common secrets and personally
identifiable information (API keys, tokens, AWS keys, JWTs, private keys,
emails, IP addresses, credit-card-like numbers, ...) and masks them, so you
can safely paste logs into bug reports, chat, or Stack Overflow.

Standard library only (Python 3.7+). See README.md for details.
"""
import argparse
import re
import sys

__version__ = "0.1.0"

# Each detector: (type_name, compiled_regex). Order matters - the most
# specific / high-entropy patterns run first so a generic catch-all does not
# clobber a more meaningful label. Detectors that capture a "value" group use
# group(1); otherwise the whole match is replaced.
_DETECTORS = [
    # PEM private key blocks (multiline).
    ("private_key",
     re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
                re.DOTALL)),
    # JSON Web Tokens: three base64url segments separated by dots.
    ("jwt",
     re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b")),
    # GitHub tokens (classic + fine-grained).
    ("github_token",
     re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b|"
                r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    # Slack tokens.
    ("slack_token",
     re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    # AWS access key id.
    ("aws_access_key",
     re.compile(r"\b(?:AKIA|ASIA|AGPA|AROA|AIPA|ANPA|ANVA)[A-Z0-9]{16}\b")),
    # Google API keys.
    ("google_api_key",
     re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    # Stripe keys.
    ("stripe_key",
     re.compile(r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    # Bearer auth header value.
    ("bearer_token",
     re.compile(r"(?i)\bBearer\s+([A-Za-z0-9._~+/=-]{12,})")),
    # Generic key=value / "key": "value" assignments for sensitive names.
    ("generic_secret",
     re.compile(r"(?i)\b(?:api[_-]?key|secret|token|passwd|password|pwd|"
                r"access[_-]?token|auth|client[_-]?secret)\b\s*[:=]\s*"
                r"[\"']?([A-Za-z0-9._\-+/=]{6,})[\"']?")),
    # Credit-card-like 13-16 digit runs (optionally space/dash separated).
    ("credit_card",
     re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    # Email addresses.
    ("email",
     re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    # IPv4 addresses.
    ("ipv4",
     re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}"
                r"(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
]

DETECTOR_TYPES = [name for name, _ in _DETECTORS]


def _luhn_ok(digits):
    """Return True if a digit string passes the Luhn checksum (real card)."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = ord(ch) - 48
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def scrub(text, mask="[REDACTED:{type}]", only=None, skip=None):
    """Redact secrets/PII in *text*.

    Returns (clean_text, counts_dict). *only*/*skip* are sets of type names.
    """
    counts = {}
    for name, pattern in _DETECTORS:
        if only is not None and name not in only:
            continue
        if skip is not None and name in skip:
            continue
        replacement = mask.replace("{type}", name)

        def _sub(m):
            # credit_card: only redact runs that pass Luhn to avoid eating IDs.
            if name == "credit_card":
                digits = re.sub(r"\D", "", m.group(0))
                if not (13 <= len(digits) <= 16 and _luhn_ok(digits)):
                    return m.group(0)
            counts[name] = counts.get(name, 0) + 1
            if m.groups():
                # Replace only the captured secret value, keep surrounding label.
                whole, val = m.group(0), m.group(1)
                return whole.replace(val, replacement, 1)
            return replacement

        text = pattern.sub(_sub, text)
    return text, counts


def _resolve_types(value, label):
    if not value:
        return None
    requested = {t.strip() for t in value.split(",") if t.strip()}
    unknown = requested - set(DETECTOR_TYPES)
    if unknown:
        sys.stderr.write(
            "logscrub: error: unknown {} type(s): {}\n".format(
                label, ", ".join(sorted(unknown))))
        sys.stderr.write("Available: " + ", ".join(DETECTOR_TYPES) + "\n")
        sys.exit(2)
    return requested


def build_parser():
    p = argparse.ArgumentParser(
        prog="logscrub",
        description="Redact secrets and PII (API keys, tokens, emails, IPs, ...) "
                    "from logs before pasting them into issues, chat, or Stack Overflow.",
        epilog="Examples:\n"
               "  cat app.log | logscrub\n"
               "  logscrub app.log -o clean.log\n"
               "  logscrub app.log --only aws_access_key,jwt --stats\n"
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
                   help="Comma-separated detector types to apply (others skipped).")
    p.add_argument("--skip", metavar="TYPES",
                   help="Comma-separated detector types to skip.")
    p.add_argument("--mask", default="[REDACTED:{type}]",
                   help="Replacement template. '{type}' is filled in. "
                        "Default: '[REDACTED:{type}]'.")
    p.add_argument("--stats", action="store_true",
                   help="Print a per-type redaction count summary to stderr.")
    p.add_argument("--list-types", action="store_true",
                   help="List available detector types and exit.")
    p.add_argument("--version", action="version", version="%(prog)s " + __version__)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_types:
        for name in DETECTOR_TYPES:
            print(name)
        return 0

    only = _resolve_types(args.only, "--only")
    skip = _resolve_types(args.skip, "--skip")

    if args.in_place and not args.files:
        parser.error("--in-place requires at least one input file")
    if args.in_place and args.output:
        parser.error("--in-place and --output are mutually exclusive")

    total = {}

    def _accumulate(c):
        for k, v in c.items():
            total[k] = total.get(k, 0) + v

    if args.in_place:
        for path in args.files:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    data = f.read()
            except OSError as e:
                sys.stderr.write("logscrub: cannot read {}: {}\n".format(path, e))
                return 1
            cleaned, counts = scrub(data, args.mask, only, skip)
            _accumulate(counts)
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(cleaned)
            except OSError as e:
                sys.stderr.write("logscrub: cannot write {}: {}\n".format(path, e))
                return 1
    else:
        if args.files:
            parts = []
            for path in args.files:
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        parts.append(f.read())
                except OSError as e:
                    sys.stderr.write("logscrub: cannot read {}: {}\n".format(path, e))
                    return 1
            data = "".join(parts)
        else:
            data = sys.stdin.read()
        cleaned, counts = scrub(data, args.mask, only, skip)
        _accumulate(counts)
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(cleaned)
            except OSError as e:
                sys.stderr.write("logscrub: cannot write {}: {}\n".format(args.output, e))
                return 1
        else:
            sys.stdout.write(cleaned)

    if args.stats:
        if total:
            sys.stderr.write("logscrub: redactions by type:\n")
            for name in DETECTOR_TYPES:
                if name in total:
                    sys.stderr.write("  {:<16} {}\n".format(name, total[name]))
            sys.stderr.write("  {:<16} {}\n".format("TOTAL", sum(total.values())))
        else:
            sys.stderr.write("logscrub: no secrets detected\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
