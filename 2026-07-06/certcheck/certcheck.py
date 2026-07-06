#!/usr/bin/env python3
"""certcheck — check TLS certificate expiry for one or more hosts.

Replaces the unmemorable:
    echo | openssl s_client -servername HOST -connect HOST:443 2>/dev/null \
         | openssl x509 -noout -dates

Standard library only. Python 3.8+.

Exit codes:
    0  all certificates OK
    1  at least one certificate expires within --warn days
    2  at least one certificate is expired, invalid, or unreachable
"""

import argparse
import concurrent.futures
import json
import os
import socket
import ssl
import sys
import tempfile
from datetime import datetime, timezone

DEFAULT_PORT = 443
DEFAULT_WARN_DAYS = 30
DEFAULT_TIMEOUT = 5.0

STATUS_OK = "OK"
STATUS_WARN = "EXPIRING"
STATUS_EXPIRED = "EXPIRED"
STATUS_ERROR = "ERROR"

# openssl's notAfter format, e.g. "Jun  9 12:00:00 2027 GMT"
_OPENSSL_TIME_FMT = "%b %d %H:%M:%S %Y %Z"


def parse_host(spec, default_port=DEFAULT_PORT):
    """Turn 'example.com', 'example.com:8443' or 'https://example.com/x'
    into (host, port). Raises ValueError on garbage."""
    spec = spec.strip()
    if not spec:
        raise ValueError("empty host")
    # Strip URL scheme and path if someone pastes a URL.
    if "://" in spec:
        spec = spec.split("://", 1)[1]
    spec = spec.split("/", 1)[0]
    if spec.startswith("["):  # [ipv6]:port
        host, _, rest = spec[1:].partition("]")
        port = rest.lstrip(":") or str(default_port)
    elif spec.count(":") == 1:
        host, port = spec.split(":")
    else:
        host, port = spec, str(default_port)
    if not host:
        raise ValueError(f"cannot parse host from {spec!r}")
    try:
        port_n = int(port)
        if not 0 < port_n < 65536:
            raise ValueError
    except ValueError:
        raise ValueError(f"invalid port in {spec!r}")
    return host, port_n


def _parse_not_after(not_after):
    """openssl-style timestamp -> aware datetime (UTC)."""
    dt = datetime.strptime(not_after, _OPENSSL_TIME_FMT)
    return dt.replace(tzinfo=timezone.utc)


def _decode_der_cert(der_bytes):
    """Decode a DER cert to the dict format getpeercert() returns.

    Used only on the fallback path (verification failed, e.g. the cert is
    already expired). Relies on ssl._ssl._test_decode_cert, a private but
    long-stable CPython helper; wrapped so failure degrades gracefully.
    """
    pem = ssl.DER_cert_to_PEM_cert(der_bytes)
    fd, path = tempfile.mkstemp(suffix=".pem")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(pem)
        return ssl._ssl._test_decode_cert(path)  # noqa: SLF001
    finally:
        os.unlink(path)


def get_proxy(proxy_arg=None):
    """Resolve an HTTP CONNECT proxy from --proxy or HTTPS_PROXY/https_proxy.
    Returns (host, port) or None."""
    spec = proxy_arg or os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if not spec:
        return None
    if "://" in spec:
        spec = spec.split("://", 1)[1]
    spec = spec.rstrip("/")
    host, _, port = spec.partition(":")
    return host, int(port or 3128)


def _connect(host, port, timeout, proxy):
    """Open a TCP connection to host:port, tunnelling through an HTTP
    CONNECT proxy if one is configured."""
    if not proxy:
        return socket.create_connection((host, port), timeout=timeout)
    sock = socket.create_connection(proxy, timeout=timeout)
    try:
        req = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n"
        sock.sendall(req.encode("ascii"))
        status = sock.recv(4096).split(b"\r\n", 1)[0].decode("latin-1", "replace")
        if " 200" not in status:
            raise OSError(f"proxy refused CONNECT: {status.strip()}")
        return sock
    except Exception:
        sock.close()
        raise


def fetch_cert(host, port, timeout=DEFAULT_TIMEOUT, proxy=None):
    """Return (cert_dict, verify_error). Tries a verified handshake first;
    if verification fails (expired/self-signed/...), retries unverified so
    we can still report the expiry date."""
    ctx = ssl.create_default_context()
    try:
        with _connect(host, port, timeout, proxy) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls:
                return tls.getpeercert(), None
    except ssl.SSLCertVerificationError as exc:
        verify_error = exc.verify_message or str(exc)
    # Fallback: grab the cert without verifying it.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with _connect(host, port, timeout, proxy) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            der = tls.getpeercert(binary_form=True)
    try:
        return _decode_der_cert(der), verify_error
    except Exception:
        return None, verify_error


def check_host(spec, warn_days, timeout, proxy=None):
    """Check one host spec; return a result dict (never raises)."""
    result = {
        "host": spec,
        "status": STATUS_ERROR,
        "days_left": None,
        "not_after": None,
        "issuer": None,
        "error": None,
    }
    try:
        host, port = parse_host(spec)
        result["host"] = f"{host}:{port}"
    except ValueError as exc:
        result["error"] = str(exc)
        return result

    try:
        cert, verify_error = fetch_cert(host, port, timeout, proxy)
    except (socket.timeout, TimeoutError):
        result["error"] = f"connection timed out after {timeout:g}s"
        return result
    except (OSError, ssl.SSLError) as exc:
        result["error"] = str(exc) or exc.__class__.__name__
        return result

    if cert is None:
        result["error"] = verify_error or "could not decode certificate"
        return result

    try:
        not_after = _parse_not_after(cert["notAfter"])
    except (KeyError, ValueError) as exc:
        result["error"] = f"cannot parse certificate dates: {exc}"
        return result

    issuer = dict(x[0] for x in cert.get("issuer", ()))
    result["issuer"] = issuer.get("organizationName") or issuer.get("commonName")
    result["not_after"] = not_after.strftime("%Y-%m-%d %H:%M UTC")
    delta = not_after - datetime.now(timezone.utc)
    days_left = delta.days + (1 if delta.seconds and delta.days >= 0 else 0)
    result["days_left"] = days_left

    if not_after <= datetime.now(timezone.utc):
        result["status"] = STATUS_EXPIRED
        result["error"] = verify_error
    elif verify_error:
        result["status"] = STATUS_ERROR
        result["error"] = verify_error
    elif days_left <= warn_days:
        result["status"] = STATUS_WARN
    else:
        result["status"] = STATUS_OK
    return result


def _color(status, text, enable):
    if not enable:
        return text
    codes = {STATUS_OK: "32", STATUS_WARN: "33",
             STATUS_EXPIRED: "31", STATUS_ERROR: "31"}
    return f"\033[{codes[status]}m{text}\033[0m"


def print_table(results, use_color):
    host_w = max(len("HOST"), *(len(r["host"]) for r in results))
    print(f"{'HOST':<{host_w}}  {'STATUS':<8}  {'DAYS':>5}  {'EXPIRES':<20}  ISSUER")
    for r in results:
        days = "-" if r["days_left"] is None else str(r["days_left"])
        expires = r["not_after"] or "-"
        tail = r["issuer"] or ""
        if r["error"]:
            tail = (tail + "  " if tail else "") + f"({r['error']})"
        status = _color(r["status"], f"{r['status']:<8}", use_color)
        print(f"{r['host']:<{host_w}}  {status}  {days:>5}  {expires:<20}  {tail}")


def read_hosts_file(path):
    hosts = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if line:
                hosts.append(line)
    return hosts


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="certcheck",
        description="Check TLS certificate expiry for one or more hosts.",
        epilog="Examples:\n"
               "  certcheck example.com\n"
               "  certcheck example.com:8443 https://api.example.com\n"
               "  certcheck -f hosts.txt --warn 14 --json\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("hosts", nargs="*", metavar="HOST",
                    help="host, host:port, or URL (default port 443)")
    ap.add_argument("-f", "--file", metavar="FILE",
                    help="read hosts from FILE (one per line, # comments)")
    ap.add_argument("-w", "--warn", type=int, default=DEFAULT_WARN_DAYS,
                    metavar="DAYS",
                    help=f"warn if cert expires within DAYS (default {DEFAULT_WARN_DAYS})")
    ap.add_argument("-t", "--timeout", type=float, default=DEFAULT_TIMEOUT,
                    metavar="SECS", help=f"connection timeout (default {DEFAULT_TIMEOUT:g})")
    ap.add_argument("--proxy", metavar="HOST:PORT",
                    help="HTTP CONNECT proxy (default: $HTTPS_PROXY if set; "
                         "pass --proxy '' to disable)")
    ap.add_argument("--json", action="store_true", help="output JSON instead of a table")
    ap.add_argument("--no-color", action="store_true", help="disable colored output")
    args = ap.parse_args(argv)

    hosts = list(args.hosts)
    if args.file:
        try:
            hosts.extend(read_hosts_file(args.file))
        except OSError as exc:
            ap.error(f"cannot read {args.file}: {exc}")
    if not hosts:
        ap.error("no hosts given (pass HOST arguments or --file)")

    proxy = None if args.proxy == "" else get_proxy(args.proxy)

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(hosts))) as ex:
        results = list(ex.map(
            lambda h: check_host(h, args.warn, args.timeout, proxy), hosts))

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        use_color = sys.stdout.isatty() and not args.no_color
        print_table(results, use_color)

    statuses = {r["status"] for r in results}
    if STATUS_EXPIRED in statuses or STATUS_ERROR in statuses:
        return 2
    if STATUS_WARN in statuses:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
