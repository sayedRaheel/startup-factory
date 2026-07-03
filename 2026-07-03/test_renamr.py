#!/usr/bin/env python3
"""Tests for renamr.py — run with: python3 test_renamr.py"""
import os
import subprocess
import sys
import tempfile
import unittest

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renamr.py")


def run(args, cwd):
    return subprocess.run([sys.executable, TOOL] + args,
                          cwd=cwd, capture_output=True, text=True)


class RenamrTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cwd = self.dir.name

    def tearDown(self):
        self.dir.cleanup()

    def touch(self, *names):
        for n in names:
            open(os.path.join(self.cwd, n), "w").close()

    def names(self):
        return sorted(os.listdir(self.cwd))

    def test_dry_run_changes_nothing(self):
        self.touch("IMG_1.jpg")
        r = run([r"IMG_(\d+)", r"photo_\1", "IMG_1.jpg"], self.cwd)
        self.assertEqual(r.returncode, 0)
        self.assertIn("dry-run", r.stdout)
        self.assertEqual(self.names(), ["IMG_1.jpg"])

    def test_apply_renames(self):
        self.touch("IMG_1.jpg", "IMG_2.jpg")
        r = run(["--apply", r"IMG_(\d+)", r"photo_\1", "IMG_1.jpg", "IMG_2.jpg"], self.cwd)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.names(), ["photo_1.jpg", "photo_2.jpg"])

    def test_collision_two_sources(self):
        self.touch("a.jpeg", "b.jpeg")
        r = run(["--apply", r"[ab]\.jpeg", "x.jpg", "a.jpeg", "b.jpeg"], self.cwd)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(self.names(), ["a.jpeg", "b.jpeg"])  # untouched

    def test_collision_target_exists(self):
        self.touch("IMG_3.jpg", "photo_3.jpg")
        r = run(["--apply", r"IMG_(\d+)", r"photo_\1", "IMG_3.jpg"], self.cwd)
        self.assertEqual(r.returncode, 2)

    def test_swap_within_batch_allowed(self):
        # a->b while b->a in the same batch is fine on plan level only if
        # targets are also sources; renamr treats existing-target-as-source as ok.
        self.touch("one.txt")
        r = run(["--apply", "one", "two", "one.txt"], self.cwd)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.names(), ["two.txt"])

    def test_no_match_exit_1(self):
        self.touch("a.jpeg")
        r = run(["ZZZ", "x", "a.jpeg"], self.cwd)
        self.assertEqual(r.returncode, 1)

    def test_bad_regex_exit_3(self):
        self.touch("a.jpeg")
        r = run(["([bad", "x", "a.jpeg"], self.cwd)
        self.assertEqual(r.returncode, 3)

    def test_path_separator_blocked(self):
        self.touch("a.jpeg")
        r = run(["--apply", "a", "../evil", "a.jpeg"], self.cwd)
        self.assertEqual(r.returncode, 3)
        self.assertEqual(self.names(), ["a.jpeg"])

    def test_lower_with_dash_replacement(self):
        self.touch("REPORT.TXT")
        r = run(["--apply", "--lower", ".*", "-", "REPORT.TXT"], self.cwd)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.names(), ["report.txt"])

    def test_undo_script_reverses(self):
        self.touch("my file.txt")
        r = run(["--apply", "--undo-script", "undo.sh", " ", "_", "my file.txt"], self.cwd)
        self.assertEqual(r.returncode, 0)
        self.assertIn("my_file.txt", self.names())
        subprocess.run(["sh", "undo.sh"], cwd=self.cwd, check=True)
        self.assertIn("my file.txt", self.names())


if __name__ == "__main__":
    unittest.main(verbosity=2)
