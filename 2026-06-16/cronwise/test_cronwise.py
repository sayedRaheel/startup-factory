#!/usr/bin/env python3
"""Unit tests for cronwise. Run: python3 -m unittest test_cronwise -v"""

import unittest
from datetime import datetime

import cronwise


class TestParsing(unittest.TestCase):
    def test_star_field(self):
        p = cronwise.parse_cron("* * * * *")
        self.assertEqual(p["minute"], set(range(60)))
        self.assertEqual(p["hour"], set(range(24)))

    def test_step(self):
        p = cronwise.parse_cron("*/15 * * * *")
        self.assertEqual(p["minute"], {0, 15, 30, 45})

    def test_range_and_list(self):
        p = cronwise.parse_cron("0 9 * * 1-5")
        self.assertEqual(p["day-of-week"], {1, 2, 3, 4, 5})
        p = cronwise.parse_cron("0 0 1,15 * *")
        self.assertEqual(p["day-of-month"], {1, 15})

    def test_named_fields(self):
        p = cronwise.parse_cron("0 0 1 jan-mar SUN")
        self.assertEqual(p["month"], {1, 2, 3})
        self.assertEqual(p["day-of-week"], {0})

    def test_sunday_seven_alias(self):
        self.assertEqual(
            cronwise.parse_cron("0 0 * * 7")["day-of-week"],
            cronwise.parse_cron("0 0 * * 0")["day-of-week"],
        )

    def test_macros(self):
        self.assertEqual(
            cronwise.parse_cron("@daily")["_raw"],
            cronwise.parse_cron("0 0 * * *")["_raw"],
        )

    def test_errors(self):
        for bad in ["* * * *", "60 * * * *", "0 0 * * 8",
                    "bad * * * *", "*/0 * * * *", "@bogus", "@reboot", ""]:
            with self.assertRaises(cronwise.CronError):
                cronwise.parse_cron(bad)


class TestNextRuns(unittest.TestCase):
    def test_interval(self):
        p = cronwise.parse_cron("*/15 * * * *")
        runs = cronwise.next_runs(p, datetime(2026, 6, 16, 10, 7), 3)
        self.assertEqual(
            [r.strftime("%H:%M") for r in runs], ["10:15", "10:30", "10:45"])

    def test_weekday_only(self):
        p = cronwise.parse_cron("0 9 * * 1-5")
        runs = cronwise.next_runs(p, datetime(2026, 6, 16, 10, 0), 3)
        # 2026-06-16 is a Tuesday -> next weekday 09:00 is Wed 17th
        self.assertEqual(runs[0], datetime(2026, 6, 17, 9, 0))
        self.assertTrue(all(r.weekday() < 5 for r in runs))

    def test_or_semantics(self):
        # Both DOM(13) and DOW(Fri) restricted -> match EITHER.
        p = cronwise.parse_cron("0 0 13 * 5")
        runs = cronwise.next_runs(p, datetime(2026, 7, 1, 0, 0), 6)
        days = {r.day for r in runs}
        self.assertIn(13, days)                    # the 13th (a Monday)
        self.assertTrue(any(r.weekday() == 4 for r in runs))  # a Friday


class TestDescribe(unittest.TestCase):
    def test_interval_phrase(self):
        self.assertEqual(
            cronwise.describe(cronwise.parse_cron("*/15 * * * *")),
            "Every 15 minutes")

    def test_time_phrase(self):
        self.assertTrue(
            cronwise.describe(cronwise.parse_cron("0 9 * * 1-5"))
            .startswith("At 09:00 on Monday"))


if __name__ == "__main__":
    unittest.main()
