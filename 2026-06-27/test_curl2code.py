#!/usr/bin/env python3
"""Tests for curl2code. Run: python3 test_curl2code.py"""
import unittest

import curl2code as c2c


class ParseTests(unittest.TestCase):
    def test_simple_get(self):
        p = c2c.parse_curl("curl https://example.com")
        self.assertEqual(p.url, "https://example.com")
        self.assertEqual(p.effective_method, "GET")
        self.assertIsNone(p.body)

    def test_method_explicit(self):
        p = c2c.parse_curl("curl -X DELETE https://example.com/1")
        self.assertEqual(p.effective_method, "DELETE")

    def test_data_implies_post(self):
        p = c2c.parse_curl("curl https://x.com -d 'a=1'")
        self.assertEqual(p.effective_method, "POST")
        self.assertEqual(p.body, "a=1")

    def test_multiple_data_joined(self):
        p = c2c.parse_curl("curl https://x.com -d a=1 -d b=2")
        self.assertEqual(p.body, "a=1&b=2")

    def test_headers(self):
        p = c2c.parse_curl(
            'curl -H "Accept: application/json" -H "X-Token: abc" https://x.com'
        )
        self.assertIn(("Accept", "application/json"), p.headers)
        self.assertIn(("X-Token", "abc"), p.headers)

    def test_long_flag_equals(self):
        p = c2c.parse_curl("curl --request=PUT https://x.com")
        self.assertEqual(p.effective_method, "PUT")

    def test_get_flag_moves_data_to_query(self):
        p = c2c.parse_curl("curl -G -d q=hello https://x.com/search")
        self.assertEqual(p.effective_method, "GET")
        self.assertIsNone(p.body)
        self.assertEqual(p.url, "https://x.com/search?q=hello")

    def test_cookie_and_agent(self):
        p = c2c.parse_curl(
            "curl -b 'session=1' -A 'MyAgent/1.0' https://x.com"
        )
        hdrs = dict(p.headers)
        self.assertEqual(hdrs["Cookie"], "session=1")
        self.assertEqual(hdrs["User-Agent"], "MyAgent/1.0")

    def test_line_continuations(self):
        cmd = "curl https://x.com \\\n  -H 'Accept: */*' \\\n  -d 'k=v'"
        p = c2c.parse_curl(cmd)
        self.assertEqual(p.url, "https://x.com")
        self.assertEqual(p.body, "k=v")

    def test_missing_url_raises(self):
        with self.assertRaises(c2c.CurlParseError):
            c2c.parse_curl("curl -X POST -d a=1")

    def test_empty_raises(self):
        with self.assertRaises(c2c.CurlParseError):
            c2c.parse_curl("   ")

    def test_unknown_flag_skipped(self):
        p = c2c.parse_curl("curl --compressed -k https://x.com")
        self.assertTrue(p.insecure)
        self.assertEqual(p.url, "https://x.com")


class PythonGenTests(unittest.TestCase):
    def test_get_output(self):
        p = c2c.parse_curl("curl https://example.com")
        out = c2c.to_python(p)
        self.assertIn("import requests", out)
        self.assertIn("requests.get(\"https://example.com\")", out)

    def test_json_body_uses_json_kwarg(self):
        p = c2c.parse_curl(
            "curl -X POST -H 'Content-Type: application/json' "
            "-d '{\"name\": \"bob\"}' https://x.com"
        )
        out = c2c.to_python(p)
        self.assertIn("json=json_data", out)
        self.assertIn("'name': 'bob'", out)
        # content-type header should be dropped when using json=
        self.assertNotIn("Content-Type", out)

    def test_basic_auth(self):
        p = c2c.parse_curl("curl -u user:pass https://x.com")
        out = c2c.to_python(p)
        self.assertIn("auth=('user', 'pass')", out)

    def test_form_data_uses_data_kwarg(self):
        p = c2c.parse_curl("curl -d 'a=1&b=2' https://x.com")
        out = c2c.to_python(p)
        self.assertIn("data=data", out)
        self.assertIn("requests.post", out)


class FetchGenTests(unittest.TestCase):
    def test_method_and_body(self):
        p = c2c.parse_curl("curl -X POST -d 'x=1' https://x.com")
        out = c2c.to_fetch(p)
        self.assertIn('"method": "POST"', out)
        self.assertIn('"body": "x=1"', out)
        self.assertIn("fetch(\"https://x.com\"", out)

    def test_basic_auth_header(self):
        p = c2c.parse_curl("curl -u a:b https://x.com")
        out = c2c.to_fetch(p)
        self.assertIn("Authorization", out)
        self.assertIn("Basic ", out)


class HttpieGenTests(unittest.TestCase):
    def test_json_fields(self):
        p = c2c.parse_curl(
            "curl -H 'Content-Type: application/json' "
            "-d '{\"name\": \"bob\", \"age\": 5}' https://x.com"
        )
        out = c2c.to_httpie(p)
        self.assertIn("http", out)
        self.assertIn("name=bob", out)
        self.assertIn("age:=5", out)

    def test_header_passthrough(self):
        p = c2c.parse_curl("curl -H 'Accept: application/json' https://x.com")
        out = c2c.to_httpie(p)
        self.assertIn("Accept:application/json", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
