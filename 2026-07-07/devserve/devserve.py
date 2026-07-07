#!/usr/bin/env python3
"""devserve — a zero-dependency local dev server that gets out of your way.

Static file serving with CORS headers, no-cache responses, SPA fallback,
and an optional same-origin API proxy so your frontend can call a local
backend without any CORS ceremony.

Standard library only. Python 3.8+.
"""
import argparse
import errno
import http.server
import os
import posixpath
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request

__version__ = "1.0.0"

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}


def build_handler(root, cors_origin, spa, no_cache, proxies, quiet):
    class DevServeHandler(http.server.SimpleHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=root, **kwargs)

        # ---- logging -------------------------------------------------
        def log_message(self, fmt, *args):
            if not quiet:
                sys.stderr.write("[devserve] %s\n" % (fmt % args))

        # ---- header injection ---------------------------------------
        def end_headers(self):
            if cors_origin:
                self.send_header("Access-Control-Allow-Origin", cors_origin)
                self.send_header("Access-Control-Allow-Methods",
                                 "GET, POST, PUT, PATCH, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers",
                                 "Content-Type, Authorization, X-Requested-With")
            if no_cache:
                self.send_header("Cache-Control",
                                 "no-store, no-cache, must-revalidate")
                self.send_header("Expires", "0")
            super().end_headers()

        # ---- CORS preflight ------------------------------------------
        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()

        # ---- request routing -----------------------------------------
        def _proxy_target(self):
            path = urllib.parse.urlparse(self.path).path
            for prefix, upstream in proxies:
                if path == prefix or path.startswith(prefix.rstrip("/") + "/"):
                    return prefix, upstream
            return None

        def do_GET(self):
            if self._proxy_target():
                self._proxy()
                return
            if spa and self._should_spa_fallback():
                self.path = "/index.html"
            super().do_GET()

        def do_HEAD(self):
            if self._proxy_target():
                self._proxy()
                return
            super().do_HEAD()

        def do_POST(self):
            self._proxy_or_405()

        def do_PUT(self):
            self._proxy_or_405()

        def do_PATCH(self):
            self._proxy_or_405()

        def do_DELETE(self):
            self._proxy_or_405()

        def _proxy_or_405(self):
            if self._proxy_target():
                self._proxy()
            else:
                self.send_error(405, "Method not allowed on static files")

        # ---- SPA fallback --------------------------------------------
        def _should_spa_fallback(self):
            path = urllib.parse.urlparse(self.path).path
            if path == "/" or "." in posixpath.basename(path):
                return False  # looks like a real file request
            local = self.translate_path(path)
            return not os.path.exists(local)

        # ---- proxy ----------------------------------------------------
        def _proxy(self):
            prefix, upstream = self._proxy_target()
            # Full path is preserved (like vite's proxy default):
            # /api/users -> http://upstream/api/users
            url = upstream.rstrip("/") + self.path
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None
            headers = {k: v for k, v in self.headers.items()
                       if k.lower() not in HOP_BY_HOP and k.lower() != "host"}
            req = urllib.request.Request(url, data=body, headers=headers,
                                         method=self.command)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    payload = resp.read()
                    self.send_response(resp.status)
                    for k, v in resp.getheaders():
                        if k.lower() in HOP_BY_HOP or k.lower() == "content-length":
                            continue
                        if k.lower().startswith("access-control-"):
                            continue  # ours win; avoids duplicate CORS headers
                        self.send_header(k, v)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
            except urllib.error.HTTPError as e:
                payload = e.read()
                self.send_response(e.code)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (urllib.error.URLError, OSError) as e:
                msg = ("upstream %s unreachable: %s" % (upstream, e)).encode()
                self.send_response(502)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(msg)))
                self.end_headers()
                self.wfile.write(msg)

    return DevServeHandler


def parse_proxy(spec):
    """Parse '/api=http://localhost:3000' into ('/api', url)."""
    if "=" not in spec:
        raise argparse.ArgumentTypeError(
            "proxy must look like /prefix=http://host:port (got %r)" % spec)
    prefix, upstream = spec.split("=", 1)
    if not prefix.startswith("/"):
        raise argparse.ArgumentTypeError("proxy prefix must start with '/'")
    if not upstream.startswith(("http://", "https://")):
        raise argparse.ArgumentTypeError("proxy upstream must be an http(s) URL")
    return prefix, upstream


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="devserve",
        description="Zero-dependency static dev server with CORS, no-cache, "
                    "SPA fallback, and an optional API proxy.",
        epilog="examples:\n"
               "  devserve                          # serve . on :8000 with CORS\n"
               "  devserve -d dist -p 5000 --spa    # SPA build on :5000\n"
               "  devserve --proxy /api=http://localhost:3000\n",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-d", "--dir", default=".", help="directory to serve (default: .)")
    p.add_argument("-p", "--port", type=int, default=8000, help="port (default: 8000)")
    p.add_argument("-b", "--bind", default="127.0.0.1",
                   help="address to bind (default: 127.0.0.1)")
    p.add_argument("--cors", default="*", metavar="ORIGIN",
                   help="Access-Control-Allow-Origin value (default: *)")
    p.add_argument("--no-cors", action="store_true", help="disable CORS headers")
    p.add_argument("--spa", action="store_true",
                   help="serve index.html for unknown extension-less paths")
    p.add_argument("--cache", action="store_true",
                   help="allow caching (default sends no-cache headers)")
    p.add_argument("--proxy", action="append", type=parse_proxy, default=[],
                   metavar="/PREFIX=URL",
                   help="proxy requests under /PREFIX to URL (repeatable)")
    p.add_argument("-q", "--quiet", action="store_true", help="suppress request log")
    p.add_argument("--version", action="version", version="devserve " + __version__)
    args = p.parse_args(argv)

    root = os.path.abspath(args.dir)
    if not os.path.isdir(root):
        print("devserve: error: not a directory: %s" % args.dir, file=sys.stderr)
        return 2

    handler = build_handler(
        root=root,
        cors_origin=None if args.no_cors else args.cors,
        spa=args.spa,
        no_cache=not args.cache,
        proxies=args.proxy,
        quiet=args.quiet,
    )

    try:
        httpd = http.server.ThreadingHTTPServer((args.bind, args.port), handler)
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            print("devserve: error: port %d is already in use "
                  "(try -p %d)" % (args.port, args.port + 1), file=sys.stderr)
            return 3
        print("devserve: error: %s" % e, file=sys.stderr)
        return 3

    features = []
    if not args.no_cors:
        features.append("CORS=%s" % args.cors)
    if not args.cache:
        features.append("no-cache")
    if args.spa:
        features.append("SPA fallback")
    for prefix, upstream in args.proxy:
        features.append("proxy %s -> %s" % (prefix, upstream))
    print("devserve %s serving %s" % (__version__, root))
    print("  http://%s:%d/  [%s]" % (args.bind, args.port, ", ".join(features) or "plain"))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\ndevserve: bye")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
