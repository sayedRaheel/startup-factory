#!/usr/bin/env python3
"""Unit tests for jsonshape. Run with: python3 -m unittest -v test_jsonshape"""
import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr

import jsonshape as js


class InferenceTests(unittest.TestCase):
    def test_scalars(self):
        self.assertEqual(js.schema_of("hi")["k"], "str")
        self.assertEqual(js.schema_of(3)["k"], "int")
        self.assertEqual(js.schema_of(3.5)["k"], "float")
        self.assertEqual(js.schema_of(True)["k"], "bool")
        self.assertEqual(js.schema_of(None)["k"], "null")

    def test_bool_not_int(self):
        # bool is a subclass of int; make sure it is classified as bool.
        self.assertEqual(js.schema_of(False)["k"], "bool")

    def test_object_fields(self):
        node = js.schema_of({"a": 1, "b": "x"})
        self.assertEqual(node["k"], "object")
        self.assertEqual(set(node["fields"]), {"a", "b"})

    def test_array_length(self):
        node = js.schema_of([1, 2, 3])
        self.assertEqual(node["k"], "array")
        self.assertEqual((node["lmin"], node["lmax"]), (3, 3))
        self.assertEqual(node["elem"]["k"], "int")

    def test_empty_array(self):
        node = js.schema_of([])
        self.assertIsNone(node["elem"])

    def test_optional_keys_merge(self):
        # An array of objects with differing keys should track presence.
        node = js.schema_of([{"a": 1, "b": 2}, {"a": 1}])
        self.assertEqual(node["k"], "array")
        obj = node["elem"]
        self.assertEqual(obj["samples"], 2)
        self.assertEqual(obj["fields"]["a"]["present"], 2)
        self.assertEqual(obj["fields"]["b"]["present"], 1)

    def test_union_types(self):
        node = js.schema_of([1, "x"])
        self.assertEqual(node["elem"]["k"], "union")
        self.assertEqual(node["elem"]["types"], {"int", "str"})

    def test_array_length_range(self):
        node = js.schema_of([[1], [1, 2, 3]])
        self.assertEqual(node["elem"]["k"], "array")
        self.assertEqual((node["elem"]["lmin"], node["elem"]["lmax"]), (1, 3))


class RenderTests(unittest.TestCase):
    def _tree(self, value, **kw):
        node = js.schema_of(value)
        lines = []
        js.render(node, None, "", True, lines, 0,
                  kw.get("depth"), kw.get("samples", False))
        return "\n".join(lines)

    def test_object_tree(self):
        out = self._tree({"id": 1, "tags": ["a", "b"]})
        self.assertIn("object{2}", out)
        self.assertIn("id: int", out)
        self.assertIn("tags: array[2] of str", out)

    def test_optional_marker(self):
        out = self._tree([{"a": 1, "b": 2}, {"a": 1}])
        self.assertIn("b?", out)
        self.assertIn("(1/2)", out)

    def test_depth_limit(self):
        out = self._tree({"a": {"b": {"c": 1}}}, depth=1)
        self.assertIn("…", out)
        self.assertNotIn("c:", out)

    def test_samples(self):
        out = self._tree({"name": "alice"}, samples=True)
        self.assertIn('= "alice"', out)


class CliTests(unittest.TestCase):
    def test_ndjson_merge(self):
        text = '{"a":1}\n{"a":2,"b":3}\n'
        node, count = js.load_value(text, ndjson=True)
        self.assertEqual(count, 2)
        self.assertEqual(node["fields"]["b"]["present"], 1)

    def test_invalid_json_exit_code(self):
        import sys
        old = sys.stdin
        sys.stdin = io.StringIO("{not valid}")
        try:
            buf = io.StringIO()
            with redirect_stderr(buf):
                rc = js.main(["-"])
        finally:
            sys.stdin = old
        self.assertEqual(rc, 1)
        self.assertIn("error", buf.getvalue())

    def test_empty_input_exit_code(self):
        import sys
        old = sys.stdin
        sys.stdin = io.StringIO("   ")
        try:
            with redirect_stderr(io.StringIO()):
                rc = js.main(["-"])
        finally:
            sys.stdin = old
        self.assertEqual(rc, 1)

    def test_json_output_is_valid(self):
        import sys
        old = sys.stdin
        sys.stdin = io.StringIO('{"a": [1, 2]}')
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = js.main(["--json", "-"])
        finally:
            sys.stdin = old
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["k"], "object")


if __name__ == "__main__":
    unittest.main()
