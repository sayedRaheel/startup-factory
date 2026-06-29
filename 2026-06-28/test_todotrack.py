#!/usr/bin/env python3
"""Unit tests for todotrack. Run: python3 test_todotrack.py"""
import os
import tempfile
import unittest

import todotrack as tt


class PatternTests(unittest.TestCase):
    def setUp(self):
        self.pat = tt.build_pattern(tt.DEFAULT_TAGS)

    def match(self, line):
        m = self.pat.search(line)
        return None if m is None else (m.group("tag").upper(),
                                       (m.group("author") or "").strip(),
                                       tt.clean_message(m.group("msg")))

    def test_hash_todo(self):
        self.assertEqual(self.match("# TODO: wire this up")[2], "wire this up")

    def test_slash_fixme(self):
        tag, _, msg = self.match("x = 1;  // FIXME broken")
        self.assertEqual(tag, "FIXME")
        self.assertEqual(msg, "broken")

    def test_author_capture(self):
        tag, author, msg = self.match("# TODO(sayed): refactor")
        self.assertEqual((tag, author, msg), ("TODO", "sayed", "refactor"))

    def test_html_comment_terminator_stripped(self):
        self.assertEqual(self.match("<!-- TODO: fix nav -->")[2], "fix nav")

    def test_block_comment_terminator_stripped(self):
        self.assertEqual(self.match(" * FIXME: leak here */")[2], "leak here")

    def test_case_insensitive(self):
        self.assertEqual(self.match("# todo lowercase")[0], "TODO")

    def test_no_leader_is_ignored(self):
        # The bare word should not trigger a hit without a comment leader.
        self.assertIsNone(self.match("todos = load_todos()"))

    def test_empty_message_ok(self):
        self.assertEqual(self.match("# TODO")[2], "")


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._write("a.py", "# TODO: alpha\nprint(1)  # FIXME: beta\n")
        self._write("b.js", "// HACK quick patch\nconst x = 'TODO not a comment hit';\n")
        os.makedirs(os.path.join(self.tmp, "node_modules"))
        self._write("node_modules/skip.js", "// TODO should be skipped\n")

    def _write(self, rel, content):
        path = os.path.join(self.tmp, rel)
        with open(path, "w") as fh:
            fh.write(content)

    def test_collect_finds_real_hits(self):
        hits = tt.collect(self.tmp, tt.DEFAULT_TAGS, tt.DEFAULT_SKIP_DIRS, [], False)
        tags = sorted(h["tag"] for h in hits)
        self.assertEqual(tags, ["FIXME", "HACK", "TODO"])

    def test_skip_dirs_respected(self):
        hits = tt.collect(self.tmp, tt.DEFAULT_TAGS, tt.DEFAULT_SKIP_DIRS, [], False)
        self.assertFalse(any("node_modules" in h["file"] for h in hits))

    def test_exclude_glob(self):
        hits = tt.collect(self.tmp, tt.DEFAULT_TAGS, tt.DEFAULT_SKIP_DIRS,
                          ["*.js"], False)
        self.assertTrue(all(not h["file"].endswith(".js") for h in hits))


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        with open(os.path.join(self.tmp, "f.py"), "w") as fh:
            fh.write("# FIXME: urgent\n# TODO: later\n")

    def test_fail_on_returns_1(self):
        rc = tt.main([self.tmp, "--format", "json", "--fail-on", "FIXME"])
        self.assertEqual(rc, 1)

    def test_no_fail_returns_0(self):
        rc = tt.main([self.tmp, "--format", "json"])
        self.assertEqual(rc, 0)

    def test_missing_path_returns_2(self):
        rc = tt.main(["/no/such/path/here", "--format", "json"])
        self.assertEqual(rc, 2)

    def test_output_file(self):
        out = os.path.join(self.tmp, "report.json")
        rc = tt.main([self.tmp, "--format", "json", "-o", out])
        self.assertEqual(rc, 0)
        with open(out) as fh:
            self.assertIn("FIXME", fh.read())


if __name__ == "__main__":
    unittest.main(verbosity=2)
