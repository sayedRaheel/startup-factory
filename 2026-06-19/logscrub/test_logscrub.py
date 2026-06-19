#!/usr/bin/env python3
"""Tests for logscrub. Run: python3 test_logscrub.py"""
import unittest
import logscrub


class ScrubTests(unittest.TestCase):
    def _types(self, text, **kw):
        _, counts = logscrub.scrub(text, **kw)
        return counts

    def test_email(self):
        out, c = logscrub.scrub("contact me at jane.doe@example.co.uk please")
        self.assertNotIn("jane.doe@example.co.uk", out)
        self.assertEqual(c.get("email"), 1)

    def test_aws_key(self):
        c = self._types("aws AKIAIOSFODNN7EXAMPLE end")
        self.assertEqual(c.get("aws_access_key"), 1)

    def test_jwt(self):
        jwt = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
               "eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c")
        c = self._types("Authorization token " + jwt)
        self.assertEqual(c.get("jwt"), 1)

    def test_github_pat(self):
        c = self._types("token github_pat_11ABCDEFG0abcdefghijklmnop end")
        self.assertEqual(c.get("github_token"), 1)

    def test_ipv4_valid_only(self):
        # 999.1.1.1 is not a valid octet and must not match.
        c = self._types("good 192.168.1.10 bad 999.1.1.1")
        self.assertEqual(c.get("ipv4"), 1)

    def test_generic_secret_keeps_label(self):
        out, c = logscrub.scrub("password = SuperSecret123")
        self.assertIn("password", out)            # label preserved
        self.assertNotIn("SuperSecret123", out)   # value gone
        self.assertEqual(c.get("generic_secret"), 1)

    def test_credit_card_luhn(self):
        # 4111111111111111 is a valid Luhn test card; the other is not.
        c = self._types("card 4111111111111111 notcard 1234567890123456")
        self.assertEqual(c.get("credit_card"), 1)

    def test_only_filter(self):
        c = self._types("a@b.com 10.0.0.1", only={"email"})
        self.assertEqual(c.get("email"), 1)
        self.assertNotIn("ipv4", c)

    def test_skip_filter(self):
        c = self._types("a@b.com 10.0.0.1", skip={"email"})
        self.assertNotIn("email", c)
        self.assertEqual(c.get("ipv4"), 1)

    def test_custom_mask(self):
        out, _ = logscrub.scrub("a@b.com", mask="X")
        self.assertEqual(out, "X")

    def test_clean_text_unchanged(self):
        text = "nothing secret here, just words and numbers 42"
        out, c = logscrub.scrub(text)
        self.assertEqual(out, text)
        self.assertEqual(c, {})

    def test_private_key_block(self):
        block = ("-----BEGIN RSA PRIVATE KEY-----\n"
                 "MIIBOwIBAAJBAKj34GkxFhD\n"
                 "-----END RSA PRIVATE KEY-----")
        out, c = logscrub.scrub("key:\n" + block)
        self.assertNotIn("MIIBOwIBAAJBAKj34GkxFhD", out)
        self.assertEqual(c.get("private_key"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
