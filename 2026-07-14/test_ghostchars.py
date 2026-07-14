#!/usr/bin/env python3
"""Unit tests for ghostchars. Run: python3 test_ghostchars.py"""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ghostchars  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "ghostchars.py")

SMART = 'msg = “hello–world”\n'
ZW = 'x = 1​\n'


class TestScan(unittest.TestCase):
    def test_clean_text(self):
        self.assertEqual(ghostchars.scan_text('print("ok")\n'), [])

    def test_smart_quotes_and_dash(self):
        findings = ghostchars.scan_text(SMART)
        cps = [f["codepoint"] for f in findings]
        self.assertEqual(cps, ["U+201C", "U+2013", "U+201D"])
        self.assertTrue(all(f["action"] == "replace" for f in findings))

    def test_zero_width_positions(self):
        findings = ghostchars.scan_text(ZW)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual((f["line"], f["col"], f["action"]),
                         (1, 6, "strip"))

    def test_multiline_line_numbers(self):
        findings = ghostchars.scan_text("ok\nbad here\n")
        self.assertEqual(findings[0]["line"], 2)

    def test_bidi_override_detected(self):
        findings = ghostchars.scan_text("if ok‮{\n")
        self.assertEqual(findings[0]["codepoint"], "U+202E")


class TestFix(unittest.TestCase):
    def test_fix_replaces_and_strips(self):
        self.assertEqual(ghostchars.fix_text(SMART), 'msg = "hello-world"\n')
        self.assertEqual(ghostchars.fix_text(ZW), "x = 1\n")

    def test_fix_is_idempotent(self):
        once = ghostchars.fix_text(SMART + ZW)
        self.assertEqual(ghostchars.fix_text(once), once)
        self.assertEqual(ghostchars.scan_text(once), [])

    def test_ellipsis_expansion(self):
        self.assertEqual(ghostchars.fix_text("wait…\n"), "wait...\n")


class TestCli(unittest.TestCase):
    def run_tool(self, args, stdin=None):
        return subprocess.run(
            [sys.executable, TOOL] + args,
            input=stdin, capture_output=True, text=True)

    def test_exit_codes(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".py", delete=False, encoding="utf-8") as tf:
            tf.write(SMART)
        try:
            self.assertEqual(self.run_tool([tf.name, "-q"]).returncode, 1)
            self.assertEqual(
                self.run_tool([tf.name, "--fix", "-q"]).returncode, 1)
            self.assertEqual(self.run_tool([tf.name, "-q"]).returncode, 0)
            self.assertTrue(os.path.exists(tf.name + ".bak"))
        finally:
            os.unlink(tf.name)
            if os.path.exists(tf.name + ".bak"):
                os.unlink(tf.name + ".bak")

    def test_missing_file_exit_2(self):
        self.assertEqual(
            self.run_tool(["/no/such/file", "-q"]).returncode, 2)

    def test_stdin_fix_pipeline(self):
        r = self.run_tool(["-", "--fix"], stdin=SMART)
        self.assertEqual(r.stdout, 'msg = "hello-world"\n')

    def test_json_output(self):
        import json
        with tempfile.NamedTemporaryFile(
                "w", suffix=".py", delete=False, encoding="utf-8") as tf:
            tf.write(ZW)
        try:
            r = self.run_tool([tf.name, "--json"])
            data = json.loads(r.stdout)
            self.assertEqual(list(data.values())[0][0]["codepoint"],
                             "U+200B")
        finally:
            os.unlink(tf.name)

    def test_self_clean(self):
        """The tool's own source must contain no offending characters."""
        self.assertEqual(self.run_tool([TOOL, "-q"]).returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
