#!/usr/bin/env python3
"""Unit tests for mdlinks. Run with:  python3 test_mdlinks.py"""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import mdlinks


class SlugTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(mdlinks.github_slug("Hello World", {}), "hello-world")

    def test_punctuation_stripped(self):
        self.assertEqual(mdlinks.github_slug("API & Usage!", {}), "api--usage")

    def test_duplicates_numbered(self):
        seen = {}
        self.assertEqual(mdlinks.github_slug("Setup", seen), "setup")
        self.assertEqual(mdlinks.github_slug("Setup", seen), "setup-1")
        self.assertEqual(mdlinks.github_slug("Setup", seen), "setup-2")

    def test_markdown_decoration_removed(self):
        self.assertEqual(mdlinks.github_slug("Using `code` here", {}),
                         "using-code-here")


class ExtractTests(unittest.TestCase):
    def test_inline_image_and_ref(self):
        text = ("See [a](x.md) and ![img](pic.png)\n"
                "[ref]: target.md\n")
        targets = [t for _, t in mdlinks.extract_links(text)]
        self.assertEqual(targets, ["x.md", "pic.png", "target.md"])

    def test_code_fence_and_span_skipped(self):
        text = ("```\n[fake](no.md)\n```\n"
                "before `[span](no2.md)` after\n"
                "[real](yes.md)\n")
        targets = [t for _, t in mdlinks.extract_links(text)]
        self.assertEqual(targets, ["yes.md"])

    def test_angle_brackets_unwrapped(self):
        targets = [t for _, t in mdlinks.extract_links("[a](<spaced file.md>)")]
        self.assertEqual(targets, ["spaced file.md"])

    def test_title_after_target(self):
        targets = [t for _, t in
                   mdlinks.extract_links('[a](x.md "the title")')]
        self.assertEqual(targets, ["x.md"])


class AnchorTests(unittest.TestCase):
    def test_atx_setext_and_html(self):
        text = ("# Top\n\nOld Style\n=========\n\n"
                "<a name=\"legacy\"></a>\n")
        anchors = mdlinks.collect_anchors(text)
        self.assertIn("top", anchors)
        self.assertIn("old-style", anchors)
        self.assertIn("legacy", anchors)


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "sub").mkdir()
        (self.root / "guide.md").write_text(
            "# Guide\n\n## Setup\n\n## Setup\n", encoding="utf-8")
        (self.root / "ok.md").write_text(
            "[g](guide.md) [s](guide.md#setup) [d](guide.md#setup-1) "
            "[self](#heading)\n\n# Heading\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = mdlinks.main(list(argv))
        return code, buf.getvalue()

    def test_clean_tree_exits_zero(self):
        code, out = self.run_main(str(self.root), "-q")
        self.assertEqual(code, 0, out)

    def test_broken_file_and_anchor_exit_one(self):
        (self.root / "bad.md").write_text(
            "[x](missing.md) [y](guide.md#nope) [z](#gone)\n",
            encoding="utf-8")
        code, out = self.run_main(str(self.root))
        self.assertEqual(code, 1)
        self.assertEqual(out.count("BROKEN"), 3)

    def test_absolute_link_resolves_against_root(self):
        (self.root / "sub" / "deep.md").write_text(
            "[top](/guide.md)\n", encoding="utf-8")
        code, out = self.run_main(str(self.root), "-q")
        self.assertEqual(code, 0, out)

    def test_missing_path_is_usage_error(self):
        code, _ = self.run_main(str(self.root / "does-not-exist"))
        self.assertEqual(code, 2)

    def test_json_output(self):
        import json
        code, out = self.run_main(str(self.root), "--format", "json")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["broken"], [])
        self.assertGreaterEqual(data["links_checked"], 4)

    def test_encoded_space_in_path(self):
        (self.root / "my notes.md").write_text("note\n", encoding="utf-8")
        (self.root / "enc.md").write_text("[n](my%20notes.md)\n",
                                          encoding="utf-8")
        code, out = self.run_main(str(self.root), "-q")
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
