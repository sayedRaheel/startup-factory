#!/usr/bin/env python3
"""Unit tests for diskhog (stdlib unittest, no dependencies)."""
import os
import tempfile
import unittest

import diskhog


class TestHelpers(unittest.TestCase):
    def test_human(self):
        self.assertEqual(diskhog.human(0), "0 B")
        self.assertEqual(diskhog.human(512), "512 B")
        self.assertEqual(diskhog.human(1024), "1.0 KB")
        self.assertEqual(diskhog.human(1536), "1.5 KB")
        self.assertEqual(diskhog.human(1024 ** 3), "1.0 GB")

    def test_parse_size(self):
        self.assertEqual(diskhog.parse_size("2048"), 2048)
        self.assertEqual(diskhog.parse_size("1K"), 1024)
        self.assertEqual(diskhog.parse_size("1.5M"), int(1.5 * 1024 ** 2))
        self.assertEqual(diskhog.parse_size("2g"), 2 * 1024 ** 3)

    def test_parse_size_bad(self):
        with self.assertRaises(ValueError):
            diskhog.parse_size("")
        with self.assertRaises(ValueError):
            diskhog.parse_size("abc")


class TestScan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "a", "b"))
        os.makedirs(os.path.join(self.tmp, "proj", "node_modules", "dep"))
        self._write(os.path.join(self.tmp, "a", "big.bin"), 4000)
        self._write(os.path.join(self.tmp, "a", "b", "mid.bin"), 1000)
        self._write(os.path.join(self.tmp, "proj", "node_modules", "dep", "x"),
                    2000)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, path, n):
        with open(path, "wb") as f:
            f.write(b"x" * n)

    def test_dir_sizes_are_recursive(self):
        dir_sizes, files = diskhog.scan(self.tmp)
        self.assertEqual(dir_sizes[self.tmp], 7000)
        self.assertEqual(dir_sizes[os.path.join(self.tmp, "a")], 5000)
        self.assertEqual(len(files), 3)

    def test_find_reclaimable(self):
        dir_sizes, _ = diskhog.scan(self.tmp)
        rec = diskhog.find_reclaimable(dir_sizes)
        paths = [p for _, p in rec]
        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].endswith("node_modules"))
        self.assertEqual(rec[0][0], 2000)


class TestMain(unittest.TestCase):
    def test_missing_path(self):
        self.assertEqual(diskhog.main(["/no/such/path/here"]), 1)

    def test_bad_min(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(diskhog.main([d, "--min", "bogus"]), 2)

    def test_ok(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(diskhog.main([d]), 0)


if __name__ == "__main__":
    unittest.main()
