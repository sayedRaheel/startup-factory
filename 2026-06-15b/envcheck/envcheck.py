#!/usr/bin/env python3
"""envcheck - a zero-dependency pre-flight check for environment variables.

Compares a real env file (default: .env) against a template (default:
.env.example) and reports problems so your app can "fail fast" instead of
crashing later with a mysterious `undefined`. Designed to drop into a CI
pipeline or a pre-start hook.

Standard library only. No third-party dependencies.
"""

import argparse
import os
import sys

VERSION = "1.0.0"

# ---- ANSI colors (auto-disabled when not a TTY or --no-color) ----------------
class C:
    RED = "\033[31m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        cls.RED = cls.YELLOW = cls.GREEN = cls.BOLD = cls.DIM = cls.RESET = ""


def parse_env_file(path):
    """Parse a .env-style file into an ordered list of (key, value) pairs.

    Supports `KEY=value`, `export KEY=value`, comments (#), blank lines, and
    surrounding single/double quotes on values. Returns (pairs, errors) where
    pairs preserves declaration order and errors is a list of (lineno, msg).
    """
    pairs = []
    errors = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].strip()
            if "=" not in line:
                errors.append((lineno, "line is not a KEY=VALUE assignment"))
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                errors.append((lineno, "empty key"))
                continue
            # strip matching surrounding quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            pairs.append((key, value))
    return pairs, errors


def to_dict(pairs):
    """Last assignment wins, like a shell would interpret it."""
    d = {}
    for k, v in pairs:
        d[k] = v
    return d


def build_report(example_path, env_path, allow_empty, allow_extra):
    ex_pairs, ex_errs = parse_env_file(example_path)
    en_pairs, en_errs = parse_env_file(env_path)

    example = to_dict(ex_pairs)
    env = to_dict(en_pairs)

    required = list(example.keys())  # keys declared in the template
    missing = [k for k in required if k not in env]
    empty = [k for k in required if k in env and env[k] == ""]
    extra = [k for k, _ in en_pairs if k not in example]
    # de-dup extra preserving order
    seen = set()
    extra = [k for k in extra if not (k in seen or seen.add(k))]

    report = {
        "example_path": example_path,
        "env_path": env_path,
        "required_count": len(required),
        "missing": missing,
        "empty": empty if not allow_empty else [],
        "extra": extra if not allow_extra else [],
        "parse_errors": {
            example_path: ex_errs,
            env_path: en_errs,
        },
    }
    return report


def report_has_problems(report):
    return bool(
        report["missing"]
        or report["empty"]
        or report["extra"]
        or report["parse_errors"][report["example_path"]]
        or report["parse_errors"][report["env_path"]]
    )


def print_human(report):
    out = []
    miss, empty, extra = report["missing"], report["empty"], report["extra"]

    for path, errs in report["parse_errors"].items():
        for lineno, msg in errs:
            out.append(f"{C.YELLOW}! parse{C.RESET} {path}:{lineno}: {msg}")

    if miss:
        out.append(f"{C.RED}{C.BOLD}MISSING{C.RESET} ({len(miss)}) "
                   f"{C.DIM}declared in template, absent from env:{C.RESET}")
        for k in miss:
            out.append(f"  {C.RED}- {k}{C.RESET}")
    if empty:
        out.append(f"{C.YELLOW}{C.BOLD}EMPTY{C.RESET} ({len(empty)}) "
                   f"{C.DIM}present but set to an empty value:{C.RESET}")
        for k in empty:
            out.append(f"  {C.YELLOW}~ {k}{C.RESET}")
    if extra:
        out.append(f"{C.YELLOW}{C.BOLD}EXTRA{C.RESET} ({len(extra)}) "
                   f"{C.DIM}in env but not declared in template:{C.RESET}")
        for k in extra:
            out.append(f"  {C.YELLOW}+ {k}{C.RESET}")

    if not report_has_problems(report):
        out.append(f"{C.GREEN}{C.BOLD}OK{C.RESET} all "
                   f"{report['required_count']} required variables present.")
    else:
        n = len(miss) + len(empty) + len(extra)
        out.append("")
        out.append(f"{C.BOLD}{n} problem(s) found{C.RESET} "
                   f"({len(miss)} missing, {len(empty)} empty, {len(extra)} extra).")
    return "\n".join(out)


def print_json(report):
    import json
    slim = {
        "ok": not report_has_problems(report),
        "env_path": report["env_path"],
        "example_path": report["example_path"],
        "required_count": report["required_count"],
        "missing": report["missing"],
        "empty": report["empty"],
        "extra": report["extra"],
        "parse_errors": {
            p: [{"line": ln, "message": m} for ln, m in errs]
            for p, errs in report["parse_errors"].items()
        },
    }
    return json.dumps(slim, indent=2)


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="envcheck",
        description="Validate a .env file against a .env.example template. "
                    "Exits non-zero when problems are found, so it works as a "
                    "CI/pre-start guard.",
        epilog="Exit codes: 0 = all good, 1 = problems found, 2 = usage/IO error.",
    )
    p.add_argument("-e", "--env", default=".env",
                   help="path to the real env file (default: .env)")
    p.add_argument("-x", "--example", default=".env.example",
                   help="path to the template file (default: .env.example)")
    p.add_argument("--allow-empty", action="store_true",
                   help="do not treat empty values as a problem")
    p.add_argument("--allow-extra", action="store_true",
                   help="do not treat undeclared (extra) keys as a problem")
    p.add_argument("--json", action="store_true",
                   help="emit a machine-readable JSON report")
    p.add_argument("-q", "--quiet", action="store_true",
                   help="print nothing; communicate via exit code only")
    p.add_argument("--no-color", action="store_true",
                   help="disable ANSI color output")
    p.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = p.parse_args(argv)

    if args.no_color or not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        C.disable()

    for label, path in (("template", args.example), ("env", args.env)):
        if not os.path.isfile(path):
            if not args.quiet:
                sys.stderr.write(f"error: {label} file not found: {path}\n")
            return 2

    try:
        report = build_report(args.example, args.env,
                              args.allow_empty, args.allow_extra)
    except OSError as exc:
        if not args.quiet:
            sys.stderr.write(f"error: {exc}\n")
        return 2

    if not args.quiet:
        print(print_json(report) if args.json else print_human(report))

    return 1 if report_has_problems(report) else 0


if __name__ == "__main__":
    sys.exit(main())
