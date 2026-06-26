#!/usr/bin/env python3
"""Unit tests for mdtable. Run: python3 test_mdtable.py"""

import unittest

import mdtable as m


class TestSplitRow(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(m.split_row("| a | b | c |"), ["a", "b", "c"])

    def test_no_outer_pipes(self):
        self.assertEqual(m.split_row("a | b"), ["a", "b"])

    def test_escaped_pipe(self):
        self.assertEqual(m.split_row(r"| a \| b | c |"), [r"a \| b", "c"])


class TestDelimiter(unittest.TestCase):
    def test_is_delimiter(self):
        self.assertTrue(m.is_delimiter_row("| --- | :---: | ---: |"))
        self.assertTrue(m.is_delimiter_row("|---|---|"))

    def test_not_delimiter(self):
        self.assertFalse(m.is_delimiter_row("| a | b |"))
        self.assertFalse(m.is_delimiter_row("| -- x | --- |"))


class TestAlignment(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(m.parse_alignment(":---:"), m.CENTER)
        self.assertEqual(m.parse_alignment("---:"), m.RIGHT)
        self.assertEqual(m.parse_alignment(":---"), m.LEFT)
        self.assertEqual(m.parse_alignment("---"), m.LEFT)


class TestFormat(unittest.TestCase):
    def test_simple_alignment(self):
        src = "| Name | Age |\n|---|---|\n| Alice | 30 |\n| Bob | 1 |\n"
        out = m.process(src)
        expected = (
            "| Name  | Age |\n"
            "| ----- | --- |\n"
            "| Alice | 30  |\n"
            "| Bob   | 1   |\n"
        )
        self.assertEqual(out, expected)

    def test_right_and_center(self):
        src = "| a | b | c |\n| :--- | :---: | ---: |\n| 1 | 2 | 3 |\n"
        out = m.process(src)
        lines = out.split("\n")
        # center column header padded on both sides, right column right-aligned
        self.assertEqual(lines[0], "| a  |  b  |  c |")
        self.assertEqual(lines[1], "| :- | :-: | -: |")

    def test_idempotent(self):
        src = "| Name | Age |\n|---|---|\n| Alice | 30 |\n"
        once = m.process(src)
        twice = m.process(once)
        self.assertEqual(once, twice)

    def test_ragged_rows_get_padded(self):
        src = "| a | b | c |\n|---|---|---|\n| 1 |\n"
        out = m.process(src)
        # missing cells filled with blanks, three columns preserved
        self.assertEqual(out.split("\n")[2], "| 1 |   |   |")

    def test_non_table_untouched(self):
        src = "# Heading\n\nSome | text but not a table\n\nMore prose.\n"
        self.assertEqual(m.process(src), src)

    def test_table_among_prose(self):
        src = ("Intro line\n\n"
               "| k | v |\n|---|---|\n| x | 1 |\n\n"
               "Outro line\n")
        out = m.process(src)
        self.assertTrue(out.startswith("Intro line\n\n"))
        self.assertTrue(out.endswith("Outro line\n"))
        self.assertIn("| k | v |", out)

    def test_preserves_no_trailing_newline(self):
        src = "| a | b |\n|---|---|\n| 1 | 2 |"
        out = m.process(src)
        self.assertFalse(out.endswith("\n"))

    def test_escaped_pipe_preserved(self):
        src = "| col |\n|---|\n| a \\| b |\n"
        out = m.process(src)
        self.assertIn(r"a \| b", out)


class TestWidth(unittest.TestCase):
    def test_ascii(self):
        self.assertEqual(m.display_width("hello"), 5)

    def test_wide(self):
        self.assertEqual(m.display_width("你好"), 4)  # CJK = 2 each


if __name__ == "__main__":
    unittest.main(verbosity=2)
