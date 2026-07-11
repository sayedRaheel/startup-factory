#!/usr/bin/env python3
"""Unit tests for csvpeek. Run: python3 test_csvpeek.py"""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

import csvpeek


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = csvpeek.main(argv)
    return code, out.getvalue(), err.getvalue()


class CsvpeekTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(
            "w", suffix=".csv", delete=False, newline="", encoding="utf-8"
        )
        self.tmp.write('id,name,score\n1,"Doe, Jane",9.5\n2,Bob,7\n3,Ann,\n')
        self.tmp.close()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_summary_and_preview(self):
        code, out, _ = run([self.tmp.name])
        self.assertEqual(code, 0)
        self.assertIn("columns:   3", out)
        self.assertIn("rows:      3", out)
        self.assertIn("Doe, Jane", out)  # quoted comma survives

    def test_cols(self):
        code, out, _ = run([self.tmp.name, "--cols"])
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["0\tid", "1\tname", "2\tscore"])

    def test_stats(self):
        code, out, _ = run([self.tmp.name, "--stats"])
        self.assertEqual(code, 0)
        self.assertIn("float", out)          # score inferred numeric (9.5, 7)
        self.assertIn("67%", out)            # score non-null 2/3
        self.assertIn("int", out)            # id inferred int

    def test_head_limit(self):
        code, out, _ = run([self.tmp.name, "-n", "1"])
        self.assertEqual(code, 0)
        self.assertIn("… 2 more rows", out)
        self.assertNotIn("Bob", out)

    def test_semicolon_sniff_no_header(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
            f.write("1;a;x\n2;b;y\n")
            path = f.name
        try:
            code, out, _ = run([path, "--no-header"])
            self.assertEqual(code, 0)
            self.assertIn("semicolon", out)
            self.assertIn("col0", out)
            self.assertIn("rows:      2", out)
        finally:
            os.unlink(path)

    def test_missing_file(self):
        code, _, err = run(["/definitely/not/here.csv"])
        self.assertEqual(code, 1)
        self.assertIn("cannot open", err)

    def test_negative_head(self):
        code, _, err = run([self.tmp.name, "--head", "-2"])
        self.assertEqual(code, 2)
        self.assertIn("--head", err)

    def test_ragged_rows_counted(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
            f.write("a,b,c\n1,2,3\n4,5\n6,7,8,9\n")
            path = f.name
        try:
            code, out, _ = run([path])
            self.assertEqual(code, 0)
            self.assertIn("ragged", out)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
