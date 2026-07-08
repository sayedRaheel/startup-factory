#!/usr/bin/env python3
"""jwtpeek — decode and inspect JSON Web Tokens locally, without jwt.io.

JWTs are credentials. Pasting real tokens into web-based decoders risks
leaking them. jwtpeek decodes the header and payload entirely offline,
humanizes the time claims (exp / iat / nbf), and can optionally verify
an HS256 signature — all with the Python standard library.

Exit codes:
  0  decoded fine (and not expired / signature OK if checked)
  1  token is expired (--check-exp) or signature verification failed
  2  bad input (not a JWT, malformed base64/JSON, missing token)
"""

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import sys
from datetime import datetime, timezone

__version__ = "1.0.0"

TIME_CLAIMS = ("exp", "iat", "nbf")


def b64url_decode(segment: str) -> bytes:
    """Decode a base64url segment, tolerating missing padding."""
    segment = segment.strip()
    padding = -len(segment) % 4
    return base64.urlsafe_b64decode(segment + "=" * padding)


def split_token(token: str):
    """Split a compact JWT into its three segments.

    Returns (header_b64, payload_b64, signature_b64). Raises ValueError
    if the token does not have exactly three dot-separated parts.
    """
    token = token.strip().strip('"').strip("'")
    # Tolerate an "Authorization: Bearer <token>" style prefix.
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError(
            f"expected 3 dot-separated segments, got {len(parts)} "
            "(is this really a compact JWT?)"
        )
    return parts[0], parts[1], parts[2]


def decode_segment(segment: str, what: str) -> dict:
    """Base64url-decode a segment and parse it as a JSON object."""
    try:
        raw = b64url_decode(segment)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{what}: invalid base64url ({exc})") from exc
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"{what}: not valid JSON ({exc})") from exc
    if not isinstance(obj, dict):
        raise ValueError(f"{what}: JSON is not an object")
    return obj


def humanize_epoch(value) -> str:
    """Render an epoch-seconds claim as UTC time plus relative offset."""
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return "(not a number)"
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    delta = ts - datetime.now(tz=timezone.utc).timestamp()
    sign = "in" if delta >= 0 else "ago"
    secs = abs(int(delta))
    if secs < 120:
        rel = f"{secs}s"
    elif secs < 7200:
        rel = f"{secs // 60}m"
    elif secs < 172800:
        rel = f"{secs // 3600}h"
    else:
        rel = f"{secs // 86400}d"
    rel = f"{rel} {sign}" if sign == "ago" else f"in {rel}"
    return f"{dt.strftime('%Y-%m-%d %H:%M:%S')} UTC ({rel})"


def is_expired(payload: dict) -> bool:
    """True if the payload has a numeric exp claim in the past."""
    exp = payload.get("exp")
    try:
        return float(exp) < datetime.now(tz=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return False


def verify_hs256(header_b64: str, payload_b64: str, sig_b64: str,
                 secret: str, alg: str) -> bool:
    """Verify an HS256 signature over the signing input."""
    if alg != "HS256":
        raise ValueError(
            f"--verify only supports HS256; token alg is {alg!r}"
        )
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing_input,
                        hashlib.sha256).digest()
    actual = b64url_decode(sig_b64)
    return hmac.compare_digest(expected, actual)


def read_token(args) -> str:
    """Get the token from argv, a file, or stdin."""
    if args.token and args.token != "-":
        return args.token
    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    data = sys.stdin.read().strip()
    if not data:
        raise ValueError("no token given (pass as argument, --file, or stdin)")
    return data


def render_pretty(header: dict, payload: dict, sig_b64: str, out) -> None:
    print("Header:", file=out)
    print(json.dumps(header, indent=2, sort_keys=True), file=out)
    print("\nPayload:", file=out)
    print(json.dumps(payload, indent=2, sort_keys=True), file=out)
    times = [c for c in TIME_CLAIMS if c in payload]
    if times:
        print("\nTime claims:", file=out)
        for claim in times:
            print(f"  {claim}: {humanize_epoch(payload[claim])}", file=out)
        if "exp" in payload:
            status = "EXPIRED" if is_expired(payload) else "not expired"
            print(f"  status: {status}", file=out)
    print(f"\nSignature (base64url, not verified): {sig_b64[:24]}…"
          if len(sig_b64) > 24 else
          f"\nSignature (base64url, not verified): {sig_b64}", file=out)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jwtpeek",
        description="Decode and inspect a JWT locally — never paste "
                    "production tokens into a website again.",
        epilog="Examples:\n"
               "  jwtpeek eyJhbGciOi...            decode a token\n"
               "  pbpaste | jwtpeek                decode from clipboard/stdin\n"
               "  jwtpeek --json TOKEN | jq .sub   machine-readable output\n"
               "  jwtpeek --check-exp TOKEN        exit 1 if expired (CI-friendly)\n"
               "  jwtpeek --verify SECRET TOKEN    verify an HS256 signature",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("token", nargs="?",
                   help="the JWT (or '-' / omitted to read stdin)")
    p.add_argument("-f", "--file", help="read the token from a file")
    p.add_argument("--json", action="store_true",
                   help="output {header, payload} as JSON (for piping to jq)")
    p.add_argument("--check-exp", action="store_true",
                   help="exit with status 1 if the token is expired")
    p.add_argument("--verify", metavar="SECRET",
                   help="verify an HS256 signature with this shared secret")
    p.add_argument("--version", action="version",
                   version=f"%(prog)s {__version__}")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        token = read_token(args)
        header_b64, payload_b64, sig_b64 = split_token(token)
        header = decode_segment(header_b64, "header")
        payload = decode_segment(payload_b64, "payload")
    except (ValueError, OSError) as exc:
        print(f"jwtpeek: error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"header": header, "payload": payload}, indent=2,
                         sort_keys=True))
    else:
        render_pretty(header, payload, sig_b64, sys.stdout)

    rc = 0
    if args.verify is not None:
        try:
            ok = verify_hs256(header_b64, payload_b64, sig_b64,
                              args.verify, header.get("alg"))
        except ValueError as exc:
            print(f"jwtpeek: error: {exc}", file=sys.stderr)
            return 2
        if ok:
            print("\nSignature: VALID (HS256)", file=sys.stderr)
        else:
            print("\nSignature: INVALID", file=sys.stderr)
            rc = 1

    if args.check_exp and is_expired(payload):
        print("jwtpeek: token is EXPIRED", file=sys.stderr)
        rc = 1

    return rc


if __name__ == "__main__":
    sys.exit(main())
