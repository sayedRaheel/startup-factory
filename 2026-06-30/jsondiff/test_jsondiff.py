#!/usr/bin/env python3
"""Unit tests for jsondiff. Run with: python3 -m unittest test_jsondiff -v"""

import io
import unittest
from contextlib import redirect_stdout, redirect_stderr

import jsondiff


def ops(changes):
    """Map path -> op for easy assertions."""
    return {c.path: c.op for c in changes}


class TestDiff(unittest.TestCase):
    def test_identical(self):
        self.assertEqual(jsondiff.diff({"a": 1}, {"a": 1}), [])

    def test_key_order_is_ignored(self):
        # The whole point: reordered keys are NOT a difference.
        a = {"b": 2, "a": 1, "c": {"y": 1, "x": 2}}
        b = {"a": 1, "c": {"x": 2, "y": 1}, "b": 2}
        self.assertEqual(jsondiff.diff(a, b), [])

    def test_added_and_removed_keys(self):
        c = jsondiff.diff({"keep": 1, "gone": 2}, {"keep": 1, "new": 3})
        m = ops(c)
        self.assertEqual(m["root.gone"], "removed")
        self.assertEqual(m["root.new"], "added")

    def test_changed_scalar(self):
        c = jsondiff.diff({"a": 1}, {"a": 2})
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0].op, "changed")
        self.assertEqual((c[0].old, c[0].new), (1, 2))

    def test_type_change(self):
        c = jsondiff.diff({"a": "1"}, {"a": 1})
        self.assertEqual(c[0].op, "changed")

    def test_int_float_equivalence(self):
        # 1 and 1.0 are semantically the same number.
        self.assertEqual(jsondiff.diff({"a": 1}, {"a": 1.0}), [])

    def test_bool_is_not_a_number(self):
        c = jsondiff.diff({"a": True}, {"a": 1})
        self.assertEqual(len(c), 1)

    def test_nested_path(self):
        c = jsondiff.diff(
            {"users": [{"name": "ann"}]},
            {"users": [{"name": "bob"}]},
        )
        self.assertEqual(c[0].path, "root.users[0].name")

    def test_array_length_diff(self):
        c = jsondiff.diff({"x": [1, 2]}, {"x": [1, 2, 3]})
        m = ops(c)
        self.assertEqual(m["root.x[2]"], "added")

    def test_array_order_matters_by_default(self):
        c = jsondiff.diff([1, 2, 3], [3, 2, 1])
        self.assertTrue(any(x.op == "changed" for x in c))

    def test_ignore_array_order(self):
        self.assertEqual(
            jsondiff.diff([1, 2, 3], [3, 2, 1], ignore_array_order=True), []
        )

    def test_ignore_array_order_detects_membership(self):
        c = jsondiff.diff([1, 2], [2, 3], ignore_array_order=True)
        m = [(x.op, x.old if x.op == "removed" else x.new) for x in c]
        self.assertIn(("removed", 1), m)
        self.assertIn(("added", 3), m)

    def test_non_identifier_key_quoting(self):
        c = jsondiff.diff({"a b": 1}, {"a b": 2})
        self.assertEqual(c[0].path, 'root["a b"]')

    def test_summary(self):
        c = jsondiff.diff({"a": 1, "b": 2}, {"a": 9, "c": 3})
        s = jsondiff.summary(c)
        self.assertIn("added", s)
        self.assertIn("3 difference", s)


class TestRender(unittest.TestCase):
    def test_text_render_no_color(self):
        c = jsondiff.diff({"a": 1}, {"a": 2})
        out = jsondiff.render_text(c, use_color=False)
        self.assertIn("~ root.a: 1 -> 2", out)

    def test_text_render_color_has_escape(self):
        c = jsondiff.diff({"a": 1}, {"b": 2})
        out = jsondiff.render_text(c, use_color=True)
        self.assertIn("\033[", out)


class TestCLI(unittest.TestCase):
    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = jsondiff.main(argv)
        return code, out.getvalue(), err.getvalue()

    def setUp(self):
        import tempfile, os, json

        self.tmp = tempfile.mkdtemp()
        self.a = os.path.join(self.tmp, "a.json")
        self.b = os.path.join(self.tmp, "b.json")
        with open(self.a, "w") as f:
            json.dump({"name": "svc", "port": 8080, "tags": ["x", "y"]}, f)
        with open(self.b, "w") as f:
            json.dump({"port": 9090, "name": "svc", "tags": ["x", "y"]}, f)

    def test_exit_diff(self):
        code, out, _ = self._run([self.a, self.b])
        self.assertEqual(code, jsondiff.EXIT_DIFF)
        self.assertIn("root.port", out)

    def test_exit_same(self):
        code, out, _ = self._run([self.a, self.a])
        self.assertEqual(code, jsondiff.EXIT_SAME)
        self.assertIn("No differences", out)

    def test_json_format(self):
        import json

        code, out, _ = self._run([self.a, self.b, "--format", "json"])
        data = json.loads(out)
        self.assertTrue(any(d["path"] == "root.port" for d in data))

    def test_quiet(self):
        code, out, _ = self._run([self.a, self.b, "--quiet"])
        self.assertEqual(code, jsondiff.EXIT_DIFF)
        self.assertEqual(out, "")

    def test_missing_file(self):
        code, _, err = self._run([self.a, "/nope/missing.json"])
        self.assertEqual(code, jsondiff.EXIT_ERROR)
        self.assertIn("file not found", err)

    def test_invalid_json(self):
        import os

        bad = os.path.join(self.tmp, "bad.json")
        with open(bad, "w") as f:
            f.write("{not valid")
        code, _, err = self._run([self.a, bad])
        self.assertEqual(code, jsondiff.EXIT_ERROR)
        self.assertIn("invalid JSON", err)


if __name__ == "__main__":
    unittest.main()
