#!/usr/bin/env python3
"""Tests for devserve: spins up real servers on ephemeral ports."""
import http.server
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import devserve


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start(handler_kwargs, root):
    handler = devserve.build_handler(root=root, quiet=True, **handler_kwargs)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, "http://127.0.0.1:%d" % httpd.server_address[1]


class UpstreamHandler(http.server.BaseHTTPRequestHandler):
    """Fake backend for proxy tests."""
    def log_message(self, *a):
        pass

    def _reply(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode() if length else ""
        payload = json.dumps({"method": self.command, "path": self.path,
                              "body": body}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = do_DELETE = _reply


class DevServeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp()
        with open(os.path.join(cls.root, "index.html"), "w") as f:
            f.write("<h1>home</h1>")
        with open(os.path.join(cls.root, "app.js"), "w") as f:
            f.write("console.log(1)")
        cls.upstream = http.server.ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
        threading.Thread(target=cls.upstream.serve_forever, daemon=True).start()
        cls.upstream_url = "http://127.0.0.1:%d" % cls.upstream.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.upstream.shutdown()
        shutil.rmtree(cls.root)

    def serve(self, **kw):
        defaults = dict(cors_origin="*", spa=False, no_cache=True, proxies=[])
        defaults.update(kw)
        httpd, url = start(defaults, self.root)
        self.addCleanup(httpd.shutdown)
        return url

    def test_cors_and_nocache_headers(self):
        url = self.serve()
        r = urllib.request.urlopen(url + "/index.html")
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "*")
        self.assertIn("no-store", r.headers["Cache-Control"])

    def test_no_cors_flag(self):
        url = self.serve(cors_origin=None)
        r = urllib.request.urlopen(url + "/index.html")
        self.assertIsNone(r.headers["Access-Control-Allow-Origin"])

    def test_options_preflight(self):
        url = self.serve()
        req = urllib.request.Request(url + "/anything", method="OPTIONS")
        r = urllib.request.urlopen(req)
        self.assertEqual(r.status, 204)
        self.assertIn("POST", r.headers["Access-Control-Allow-Methods"])

    def test_spa_fallback(self):
        url = self.serve(spa=True)
        r = urllib.request.urlopen(url + "/some/client/route")
        self.assertIn(b"home", r.read())

    def test_spa_does_not_mask_real_files(self):
        url = self.serve(spa=True)
        r = urllib.request.urlopen(url + "/app.js")
        self.assertIn(b"console", r.read())

    def test_spa_missing_asset_is_404(self):
        url = self.serve(spa=True)
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(url + "/missing.png")
        self.assertEqual(cm.exception.code, 404)

    def test_post_without_proxy_is_405(self):
        url = self.serve()
        req = urllib.request.Request(url + "/index.html", data=b"x", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code, 405)

    def test_proxy_get_and_post(self):
        url = self.serve(proxies=[("/api", self.upstream_url)])
        got = json.loads(urllib.request.urlopen(url + "/api/users?x=1").read())
        self.assertEqual(got["path"], "/api/users?x=1")
        req = urllib.request.Request(url + "/api/users", data=b'{"a":1}', method="POST")
        got = json.loads(urllib.request.urlopen(req).read())
        self.assertEqual(got["method"], "POST")
        self.assertEqual(got["body"], '{"a":1}')

    def test_proxy_response_still_has_cors(self):
        url = self.serve(proxies=[("/api", self.upstream_url)])
        r = urllib.request.urlopen(url + "/api/ping")
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "*")

    def test_proxy_upstream_down_is_502(self):
        url = self.serve(proxies=[("/api", "http://127.0.0.1:%d" % free_port())])
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(url + "/api/ping")
        self.assertEqual(cm.exception.code, 502)

    def test_parse_proxy_validation(self):
        self.assertEqual(devserve.parse_proxy("/api=http://x:1"), ("/api", "http://x:1"))
        for bad in ("noequals", "api=http://x", "/api=ftp://x"):
            with self.assertRaises(Exception):
                devserve.parse_proxy(bad)

    def test_main_bad_dir_exit_code(self):
        self.assertEqual(devserve.main(["-d", "/nonexistent-dir-xyz"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
