#!/usr/bin/env python3
"""Unit tests for certcheck's pure helpers (no network required)."""

import unittest
from datetime import timezone

import certcheck


class TestParseHost(unittest.TestCase):
    def test_bare_host(self):
        self.assertEqual(certcheck.parse_host("example.com"), ("example.com", 443))

    def test_host_with_port(self):
        self.assertEqual(certcheck.parse_host("example.com:8443"), ("example.com", 8443))

    def test_https_url(self):
        self.assertEqual(
            certcheck.parse_host("https://api.example.com/v1/x?y=1"),
            ("api.example.com", 443),
        )

    def test_ipv6_with_port(self):
        self.assertEqual(certcheck.parse_host("[2606:2800::1]:8443"), ("2606:2800::1", 8443))

    def test_ipv6_default_port(self):
        self.assertEqual(certcheck.parse_host("[2606:2800::1]"), ("2606:2800::1", 443))

    def test_whitespace_stripped(self):
        self.assertEqual(certcheck.parse_host("  example.com \n"), ("example.com", 443))

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            certcheck.parse_host("   ")

    def test_bad_port_raises(self):
        for bad in ("example.com:0", "example.com:70000", "example.com:abc"):
            with self.assertRaises(ValueError):
                certcheck.parse_host(bad)


class TestNotAfterParsing(unittest.TestCase):
    def test_openssl_format(self):
        dt = certcheck._parse_not_after("Jun  9 12:00:00 2027 GMT")
        self.assertEqual((dt.year, dt.month, dt.day, dt.hour), (2027, 6, 9, 12))
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            certcheck._parse_not_after("not a date")


class TestHostsFile(unittest.TestCase):
    def test_comments_and_blanks(self):
        import tempfile, os
        fd, path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write("# comment\n\nexample.com\napi.example.com:8443  # inline\n")
            self.assertEqual(
                certcheck.read_hosts_file(path),
                ["example.com", "api.example.com:8443"],
            )
        finally:
            os.unlink(path)


class TestCheckHostErrors(unittest.TestCase):
    def test_unparseable_spec_is_error_not_crash(self):
        r = certcheck.check_host("::bad::spec::", 30, 1.0)
        self.assertEqual(r["status"], certcheck.STATUS_ERROR)
        self.assertIsNotNone(r["error"])


if __name__ == "__main__":
    unittest.main()
