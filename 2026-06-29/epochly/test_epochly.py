#!/usr/bin/env python3
"""Unit tests for epochly. Run with: python3 -m unittest -v test_epochly"""

import io
import json
import unittest
from contextlib import redirect_stdout
from datetime import timedelta

import epochly


class TestUnitDetection(unittest.TestCase):
    def test_seconds(self):
        self.assertEqual(epochly.detect_unit("1704067200"), "s")

    def test_millis(self):
        self.assertEqual(epochly.detect_unit("1704067200000"), "ms")

    def test_micros(self):
        self.assertEqual(epochly.detect_unit("1704067200000000"), "us")

    def test_nanos(self):
        self.assertEqual(epochly.detect_unit("1704067200000000000"), "ns")


class TestEpochToDatetime(unittest.TestCase):
    def test_known_instant_seconds(self):
        dt, unit = epochly.epoch_to_datetime("1704067200", None)
        self.assertEqual(unit, "s")
        self.assertEqual(dt.isoformat(), "2024-01-01T00:00:00+00:00")

    def test_millis_auto(self):
        dt, unit = epochly.epoch_to_datetime("1704067200000", None)
        self.assertEqual(unit, "ms")
        self.assertEqual(dt.isoformat(), "2024-01-01T00:00:00+00:00")

    def test_forced_unit(self):
        # 1704067200 forced as millis -> a 1970-era instant, not 2024.
        dt, unit = epochly.epoch_to_datetime("1704067200", "ms")
        self.assertEqual(unit, "ms")
        self.assertEqual(dt.year, 1970)

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            epochly.epoch_to_datetime("9" * 30, "s")


class TestDateStringParsing(unittest.TestCase):
    def test_iso_with_z(self):
        dt = epochly.parse_datestring("2024-01-01T00:00:00Z")
        self.assertEqual(int(dt.timestamp()), 1704067200)

    def test_iso_naive_assumed_utc(self):
        dt = epochly.parse_datestring("2024-01-01")
        self.assertEqual(int(dt.timestamp()), 1704067200)

    def test_space_separated(self):
        dt = epochly.parse_datestring("2024-01-01 12:00:00")
        self.assertEqual(int(dt.timestamp()), 1704067200 + 12 * 3600)

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            epochly.parse_datestring("not a date")


class TestHumanize(unittest.TestCase):
    def test_seconds_ago(self):
        self.assertEqual(epochly.humanize_delta(timedelta(seconds=-30)),
                         "30 seconds ago")

    def test_future(self):
        self.assertTrue(
            epochly.humanize_delta(timedelta(hours=2)).startswith("in 2 hours"))

    def test_now(self):
        self.assertEqual(epochly.humanize_delta(timedelta(seconds=0)), "just now")

    def test_duration(self):
        self.assertEqual(
            epochly.humanize_duration(timedelta(days=1, hours=1)),
            "1 day, 1 hour")


class TestRoundTrip(unittest.TestCase):
    def test_epoch_to_date_to_epoch(self):
        dt, _ = epochly.epoch_to_datetime("1704067200", None)
        back = epochly.parse_datestring(dt.isoformat())
        self.assertEqual(int(back.timestamp()), 1704067200)


class TestCLI(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = epochly.main(argv)
        return code, buf.getvalue()

    def test_convert_json(self):
        code, out = self._run(["1704067200", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["epoch_seconds"], 1704067200)
        self.assertEqual(data["iso_utc"], "2024-01-01T00:00:00Z")

    def test_diff(self):
        code, out = self._run(["diff", "1704067200", "1704153600"])
        self.assertEqual(code, 0)
        self.assertIn("1 day", out)

    def test_now_runs(self):
        code, out = self._run(["now", "--json"])
        self.assertEqual(code, 0)
        self.assertIn("epoch_seconds", out)

    def test_bad_value_exit_code(self):
        code, _ = self._run(["definitely-not-a-date"])
        self.assertEqual(code, 1)

    def test_no_args_prints_help(self):
        code, _ = self._run([])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
