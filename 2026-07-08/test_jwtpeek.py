#!/usr/bin/env python3
"""Tests for jwtpeek — stdlib unittest, no network, no dependencies."""

import base64
import hashlib
import hmac
import io
import json
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout

import jwtpeek


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_token(payload: dict, secret: str = "s3cret", alg: str = "HS256") -> str:
    header = {"alg": alg, "typ": "JWT"}
    h = b64url(json.dumps(header).encode())
    p = b64url(json.dumps(payload).encode())
    sig = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{b64url(sig)}"


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = jwtpeek.main(argv)
    return rc, out.getvalue(), err.getvalue()


class DecodeTests(unittest.TestCase):
    def test_decodes_header_and_payload(self):
        tok = make_token({"sub": "alice", "role": "admin"})
        rc, out, _ = run([tok])
        self.assertEqual(rc, 0)
        self.assertIn('"sub": "alice"', out)
        self.assertIn('"alg": "HS256"', out)

    def test_json_output_is_parseable(self):
        tok = make_token({"sub": "bob"})
        rc, out, _ = run(["--json", tok])
        self.assertEqual(rc, 0)
        doc = json.loads(out)
        self.assertEqual(doc["payload"]["sub"], "bob")
        self.assertEqual(doc["header"]["typ"], "JWT")

    def test_bearer_prefix_tolerated(self):
        tok = make_token({"sub": "carol"})
        rc, out, _ = run([f"Bearer {tok}"])
        self.assertEqual(rc, 0)
        self.assertIn('"sub": "carol"', out)

    def test_missing_padding_ok(self):
        # b64url segments legitimately lack '=' padding; must still decode.
        tok = make_token({"x": "y" * 5})
        self.assertNotIn("=", tok)
        rc, _, _ = run([tok])
        self.assertEqual(rc, 0)


class ErrorTests(unittest.TestCase):
    def test_not_a_jwt(self):
        rc, _, err = run(["hello.world"])
        self.assertEqual(rc, 2)
        self.assertIn("3 dot-separated segments", err)

    def test_garbage_base64(self):
        rc, _, err = run(["!!!.@@@.###"])
        self.assertEqual(rc, 2)
        self.assertIn("error", err)

    def test_non_json_payload(self):
        h = b64url(json.dumps({"alg": "none"}).encode())
        p = b64url(b"not json at all")
        rc, _, err = run([f"{h}.{p}.sig"])
        self.assertEqual(rc, 2)
        self.assertIn("payload", err)


class ExpiryTests(unittest.TestCase):
    def test_expired_flagged(self):
        tok = make_token({"exp": int(time.time()) - 3600})
        rc, out, err = run(["--check-exp", tok])
        self.assertEqual(rc, 1)
        self.assertIn("EXPIRED", out + err)

    def test_valid_not_flagged(self):
        tok = make_token({"exp": int(time.time()) + 3600})
        rc, out, _ = run(["--check-exp", tok])
        self.assertEqual(rc, 0)
        self.assertIn("not expired", out)

    def test_no_exp_claim_is_fine(self):
        tok = make_token({"sub": "dave"})
        rc, _, _ = run(["--check-exp", tok])
        self.assertEqual(rc, 0)


class VerifyTests(unittest.TestCase):
    def test_good_signature(self):
        tok = make_token({"sub": "eve"}, secret="topsecret")
        rc, _, err = run(["--verify", "topsecret", tok])
        self.assertEqual(rc, 0)
        self.assertIn("VALID", err)

    def test_bad_signature(self):
        tok = make_token({"sub": "eve"}, secret="topsecret")
        rc, _, err = run(["--verify", "wrongsecret", tok])
        self.assertEqual(rc, 1)
        self.assertIn("INVALID", err)

    def test_non_hs256_rejected(self):
        tok = make_token({"sub": "frank"}, alg="RS256")
        rc, _, err = run(["--verify", "whatever", tok])
        self.assertEqual(rc, 2)
        self.assertIn("HS256", err)


class HumanizeTests(unittest.TestCase):
    def test_epoch_renders_utc(self):
        s = jwtpeek.humanize_epoch(0)
        self.assertIn("1970-01-01 00:00:00 UTC", s)

    def test_non_numeric(self):
        self.assertIn("not a number", jwtpeek.humanize_epoch("soon"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
