#!/usr/bin/env python3
"""Tests for dupefind. Run: python3 test_dupefind.py"""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dupefind  # noqa: E402


def write(path, data: bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


class HumanSizeTests(unittest.TestCase):
    def test_units(self):
        self.assertEqual(dupefind.human_size(512), "512 B")
        self.assertEqual(dupefind.human_size(1536), "1.5 KB")
        self.assertEqual(dupefind.human_size(1048576), "1.0 MB")


class FindDuplicatesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dupefind_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_detects_identical_content(self):
        write(os.path.join(self.tmp, "a.txt"), b"hello world")
        write(os.path.join(self.tmp, "sub/b.txt"), b"hello world")
        write(os.path.join(self.tmp, "c.txt"), b"unique")
        files = list(dupefind.iter_files([self.tmp]))
        groups = dupefind.find_duplicates(files)
        self.assertEqual(len(groups), 1)
        size, paths = groups[0]
        self.assertEqual(len(paths), 2)
        self.assertTrue(all(p.endswith(".txt") for p in paths))

    def test_same_size_different_content_not_duplicate(self):
        write(os.path.join(self.tmp, "a.bin"), b"AAAA")
        write(os.path.join(self.tmp, "b.bin"), b"BBBB")  # same size, diff bytes
        groups = dupefind.find_duplicates(list(dupefind.iter_files([self.tmp])))
        self.assertEqual(groups, [])

    def test_min_size_filter(self):
        write(os.path.join(self.tmp, "a.txt"), b"x")
        write(os.path.join(self.tmp, "b.txt"), b"x")
        groups = dupefind.find_duplicates(
            list(dupefind.iter_files([self.tmp])), min_size=10)
        self.assertEqual(groups, [])

    def test_hidden_excluded_by_default(self):
        write(os.path.join(self.tmp, ".secret"), b"dupe")
        write(os.path.join(self.tmp, "plain"), b"dupe")
        files = list(dupefind.iter_files([self.tmp]))
        self.assertNotIn(os.path.join(self.tmp, ".secret"), files)

    def test_large_files_streamed(self):
        big = b"Z" * (dupefind._PARTIAL_BYTES + 1000)
        write(os.path.join(self.tmp, "big1"), big)
        write(os.path.join(self.tmp, "big2"), big)
        groups = dupefind.find_duplicates(list(dupefind.iter_files([self.tmp])))
        self.assertEqual(len(groups), 1)

    def test_exit_codes(self):
        write(os.path.join(self.tmp, "a"), b"same")
        write(os.path.join(self.tmp, "b"), b"same")
        with redirect_stdout(io.StringIO()):
            rc = dupefind.main([self.tmp, "-q"])
        self.assertEqual(rc, 1)  # duplicates found
        os.remove(os.path.join(self.tmp, "b"))
        with redirect_stdout(io.StringIO()):
            rc = dupefind.main([self.tmp, "-q"])
        self.assertEqual(rc, 0)  # none left

    def test_json_output(self):
        write(os.path.join(self.tmp, "a"), b"jsondupe")
        write(os.path.join(self.tmp, "b"), b"jsondupe")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = dupefind.main([self.tmp, "--json"])
        import json
        data = json.loads(buf.getvalue())
        self.assertEqual(rc, 1)
        self.assertEqual(data["group_count"], 1)
        self.assertEqual(data["wasted_bytes"], len(b"jsondupe"))

    def test_missing_path_warns_not_crash(self):
        with redirect_stdout(io.StringIO()):
            rc = dupefind.main(["/no/such/path/here", "-q"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
