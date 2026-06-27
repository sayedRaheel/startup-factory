#!/usr/bin/env python3
"""curl2code - convert a cURL command into runnable code.

Paste the "Copy as cURL" output from your browser's DevTools (or any curl
command) and get equivalent Python (requests), JavaScript (fetch), or HTTPie
code back. Runs entirely offline with the standard library only, so auth
headers and tokens never leave your machine.

Usage examples are in the README. See `curl2code --help`.
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

__version__ = "1.0.0"

# Flags that take a value (long + short forms).
_VALUE_FLAGS = {
    "-X", "--request",
    "-H", "--header",
    "-d", "--data", "--data-raw", "--data-ascii", "--data-binary",
    "--data-urlencode",
    "-u", "--user",
    "-b", "--cookie",
    "-A", "--user-agent",
    "-e", "--referer",
    "--url",
    "--connect-timeout", "--max-time",
}

# Boolean flags we recognise (consume no value).
_BOOL_FLAGS = {
    "--compressed",
    "-k", "--insecure",
    "-L", "--location",
    "-G", "--get",
    "-I", "--head",
    "-s", "--silent",
    "-f", "--fail",
    "-v", "--verbose",
    "-i", "--include",
    "-#", "--progress-bar",
}


class CurlParseError(ValueError):
    """Raised when the curl command cannot be understood."""


class ParsedCurl:
    """A structured representation of a curl command."""

    def __init__(self) -> None:
        self.method: str | None = None
        self.url: str | None = None
        self.headers: list[tuple[str, str]] = []
        self.data: list[str] = []
        self.data_is_urlencode: bool = False
        self.user: str | None = None
        self.insecure: bool = False
        self.compressed: bool = False
        self.force_get: bool = False
        self.head: bool = False

    @property
    def effective_method(self) -> str:
        if self.method:
            return self.method.upper()
        if self.head:
            return "HEAD"
        if self.data and not self.force_get:
            return "POST"
        return "GET"

    @property
    def body(self) -> str | None:
        if not self.data:
            return None
        # curl joins multiple -d values with '&'.
        return "&".join(self.data)


def _strip_curl_prefix(tokens: list[str]) -> list[str]:
    # Drop a leading "curl" token if present, plus any line-continuation
    # backslashes that survived tokenisation.
    out = [t for t in tokens if t != "\\"]
    if out and out[0] == "curl":
        out = out[1:]
    return out


def parse_curl(command: str) -> ParsedCurl:
    """Parse a curl command string into a ParsedCurl object."""
    command = command.strip()
    if not command:
        raise CurlParseError("empty command")
    # Normalise line continuations so shlex sees one logical line.
    command = command.replace("\\\n", " ")
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        raise CurlParseError(f"could not tokenise command: {exc}") from exc

    tokens = _strip_curl_prefix(tokens)
    if not tokens:
        raise CurlParseError("no curl arguments found")

    parsed = ParsedCurl()
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]

        # Support --flag=value style.
        flag, eq, inline_val = tok.partition("=")
        if eq and flag in _VALUE_FLAGS:
            value = inline_val
            tok = flag
        elif tok in _VALUE_FLAGS:
            if i + 1 >= n:
                raise CurlParseError(f"flag {tok} expects a value")
            value = tokens[i + 1]
            i += 1
        else:
            value = None

        if tok in ("-X", "--request"):
            parsed.method = value
        elif tok in ("-H", "--header"):
            name, sep, val = value.partition(":")
            if sep:
                parsed.headers.append((name.strip(), val.strip()))
            else:
                # Header with no colon (rare) - keep as-is.
                parsed.headers.append((name.strip(), ""))
        elif tok in ("-d", "--data", "--data-raw", "--data-ascii",
                     "--data-binary"):
            parsed.data.append(value)
        elif tok == "--data-urlencode":
            parsed.data.append(value)
            parsed.data_is_urlencode = True
        elif tok in ("-u", "--user"):
            parsed.user = value
        elif tok in ("-b", "--cookie"):
            parsed.headers.append(("Cookie", value))
        elif tok in ("-A", "--user-agent"):
            parsed.headers.append(("User-Agent", value))
        elif tok in ("-e", "--referer"):
            parsed.headers.append(("Referer", value))
        elif tok == "--url":
            parsed.url = value
        elif tok in ("--connect-timeout", "--max-time"):
            pass  # recognised but not emitted
        elif tok in ("-G", "--get"):
            parsed.force_get = True
        elif tok in ("-I", "--head"):
            parsed.head = True
        elif tok in ("-k", "--insecure"):
            parsed.insecure = True
        elif tok == "--compressed":
            parsed.compressed = True
        elif tok in _BOOL_FLAGS:
            pass  # recognised, no effect on generated code
        elif tok.startswith("-") and tok != "-":
            # Unknown flag: skip it rather than crashing. If the next token
            # is not itself a flag we leave it - it may be a URL.
            pass
        else:
            # Positional argument -> the URL (first one wins).
            if parsed.url is None:
                parsed.url = tok
        i += 1

    if parsed.url is None:
        raise CurlParseError("no URL found in command")

    # With -G/--get, curl moves any -d data into the URL query string
    # instead of the body. Mirror that so generated code is correct.
    if parsed.force_get and parsed.data:
        existing = parsed.body or ""
        u = urlparse(parsed.url)
        merged = parse_qsl(u.query, keep_blank_values=True)
        merged += parse_qsl(existing, keep_blank_values=True)
        parsed.url = urlunparse(u._replace(query=urlencode(merged)))
        parsed.data = []

    return parsed


# --------------------------------------------------------------------------
# Code generators
# --------------------------------------------------------------------------

def _headers_dict(parsed: ParsedCurl) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, val in parsed.headers:
        out[name] = val
    return out


def _maybe_json_body(parsed: ParsedCurl):
    """Return parsed JSON if the body looks like JSON, else None."""
    body = parsed.body
    if not body:
        return None
    headers_lower = {k.lower(): v for k, v in parsed.headers}
    ctype = headers_lower.get("content-type", "")
    looks_json = "json" in ctype or body.lstrip().startswith(("{", "["))
    if not looks_json:
        return None
    try:
        return json.loads(body)
    except (ValueError, TypeError):
        return None


def to_python(parsed: ParsedCurl) -> str:
    lines = ["import requests", ""]
    headers = _headers_dict(parsed)
    json_body = _maybe_json_body(parsed)

    if headers:
        lines.append("headers = " + _py_repr(headers))
    args = ['"%s"' % parsed.url]
    if headers:
        args.append("headers=headers")

    if json_body is not None:
        # Drop an explicit content-type header; requests sets it via json=.
        headers.pop("Content-Type", None)
        headers.pop("content-type", None)
        lines = ["import requests", ""]
        if headers:
            lines.append("headers = " + _py_repr(headers))
        lines.append("json_data = " + _py_repr(json_body))
        args = ['"%s"' % parsed.url]
        if headers:
            args.append("headers=headers")
        args.append("json=json_data")
    elif parsed.body is not None:
        lines.append("data = " + _py_repr(parsed.body))
        args.append("data=data")

    if parsed.user:
        user, _, pwd = parsed.user.partition(":")
        args.append("auth=(%r, %r)" % (user, pwd))
    if parsed.insecure:
        args.append("verify=False")

    method = parsed.effective_method.lower()
    if method not in ("get", "post", "put", "delete", "patch", "head",
                      "options"):
        # Fall back to the generic request() form for exotic verbs.
        call = "response = requests.request(%r, %s)" % (
            parsed.effective_method, ", ".join(args))
    else:
        call = "response = requests.%s(%s)" % (method, ", ".join(args))
    lines.append("")
    lines.append(call)
    lines.append("print(response.status_code)")
    lines.append("print(response.text)")
    return "\n".join(lines)


def to_fetch(parsed: ParsedCurl) -> str:
    headers = _headers_dict(parsed)
    opts: dict[str, object] = {"method": parsed.effective_method}
    if parsed.user:
        user, _, pwd = parsed.user.partition(":")
        import base64
        token = base64.b64encode(f"{user}:{pwd}".encode()).decode()
        headers["Authorization"] = "Basic " + token
    if headers:
        opts["headers"] = headers
    if parsed.body is not None:
        opts["body"] = parsed.body

    opts_js = _js_obj(opts, indent=2)
    return (
        "const response = await fetch(%s, %s);\n"
        "const text = await response.text();\n"
        "console.log(response.status, text);" % (_js_str(parsed.url), opts_js)
    )


def to_httpie(parsed: ParsedCurl) -> str:
    parts = ["http"]
    method = parsed.effective_method
    if method != "GET" or parsed.body is None:
        parts.append(method)
    parts.append(_sh_quote(parsed.url))
    for name, val in parsed.headers:
        parts.append(_sh_quote(f"{name}:{val}"))
    if parsed.user:
        parts.append("-a " + _sh_quote(parsed.user))
    if parsed.insecure:
        parts.append("--verify=no")
    body = parsed.body
    if body:
        json_body = _maybe_json_body(parsed)
        if isinstance(json_body, dict):
            for k, v in json_body.items():
                if isinstance(v, str):
                    parts.append(_sh_quote(f"{k}={v}"))
                else:
                    parts.append(_sh_quote(f"{k}:={json.dumps(v)}"))
        else:
            # Raw body via redirect.
            return " ".join(parts) + " <<< " + _sh_quote(body)
    return " ".join(parts)


# --------------------------------------------------------------------------
# Small language-specific formatting helpers
# --------------------------------------------------------------------------

def _py_repr(obj) -> str:
    return repr(obj)


def _js_str(s: str) -> str:
    return json.dumps(s)


def _js_obj(obj, indent: int = 2, level: int = 0) -> str:
    pad = " " * (indent * (level + 1))
    closing = " " * (indent * level)
    items = []
    for key, val in obj.items():
        if isinstance(val, dict):
            rendered = _js_obj(val, indent, level + 1)
        else:
            rendered = json.dumps(val)
        items.append(f"{pad}{json.dumps(key)}: {rendered}")
    if not items:
        return "{}"
    return "{\n" + ",\n".join(items) + "\n" + closing + "}"


def _sh_quote(s: str) -> str:
    return shlex.quote(s)


GENERATORS = {
    "python": to_python,
    "fetch": to_fetch,
    "httpie": to_httpie,
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="curl2code",
        description="Convert a cURL command into Python, JavaScript fetch, "
                    "or HTTPie code. Reads the command from arguments or "
                    "stdin. Standard library only - nothing leaves your "
                    "machine.",
        epilog='Example: curl2code -t python \'curl -H "Accept: '
               'application/json" https://api.example.com/users\'',
    )
    p.add_argument(
        "command", nargs="*",
        help="The curl command (quote it, or pipe it via stdin).",
    )
    p.add_argument(
        "-t", "--target", choices=sorted(GENERATORS), default="python",
        help="Output language/library (default: python).",
    )
    p.add_argument(
        "--version", action="version", version=f"curl2code {__version__}",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command:
        command = " ".join(args.command)
    elif not sys.stdin.isatty():
        command = sys.stdin.read()
    else:
        parser.print_help(sys.stderr)
        return 2

    try:
        parsed = parse_curl(command)
    except CurlParseError as exc:
        print(f"curl2code: error: {exc}", file=sys.stderr)
        return 1

    generator = GENERATORS[args.target]
    try:
        print(generator(parsed))
    except Exception as exc:  # pragma: no cover - defensive
        print(f"curl2code: failed to generate code: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
