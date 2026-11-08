"""Tahlil, tavsif va keyingi ishga tushish vaqtlari."""

import datetime as dt
import importlib.util
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, os.pardir, "cronsay.py")

spec = importlib.util.spec_from_file_location("cronsay", SCRIPT)
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)


def values(expression, index):
    return cs.parse(expression)[index].values


class ParseTest(unittest.TestCase):
    def test_a_star_covers_the_whole_range(self):
        self.assertEqual(values("* * * * *", 0), list(range(60)))
        self.assertEqual(values("* * * * *", 1), list(range(24)))

    def test_a_step_walks_the_range(self):
        self.assertEqual(values("*/15 * * * *", 0), [0, 15, 30, 45])

    def test_a_range_with_a_step(self):
        self.assertEqual(values("0-30/10 * * * *", 0), [0, 10, 20, 30])

    def test_a_list(self):
        self.assertEqual(values("0,15,42 * * * *", 0), [0, 15, 42])

    def test_a_range(self):
        self.assertEqual(values("* 9-17 * * *", 1), list(range(9, 18)))

    def test_month_names_work(self):
        self.assertEqual(values("0 0 1 JAN *", 3), [1])
        self.assertEqual(values("0 0 1 jan-mar *", 3), [1, 2, 3])

    def test_day_names_work(self):
        self.assertEqual(values("0 0 * * MON", 4), [1])
        self.assertEqual(values("0 0 * * mon-fri", 4), [1, 2, 3, 4, 5])

    def test_sunday_is_both_zero_and_seven(self):
        self.assertEqual(values("0 0 * * 7", 4), [0])
        self.assertEqual(values("0 0 * * 0,7", 4), [0])

    def test_a_value_with_a_step_runs_to_the_top(self):
        self.assertEqual(values("5/20 * * * *", 0), [5, 25, 45])

    def test_shorthand(self):
        self.assertEqual(values("@daily", 1), [0])
        self.assertEqual(values("@hourly", 0), [0])
        self.assertEqual(values("@weekly", 4), [0])

    def test_reboot_is_refused_with_an_explanation(self):
        with self.assertRaises(cs.CronError) as e:
            cs.parse("@reboot")
        self.assertIn("boot", str(e.exception))

    def test_bad_input_is_refused(self):
        for bad in ("* * * *", "* * * * * *", "60 * * * *", "* 24 * * *",
                    "*/0 * * * *", "x * * * *", "10-5 * * * *", "0 0 0 * *",
                    ", * * * *"):
            with self.assertRaises(cs.CronError, msg=bad):
                cs.parse(bad)


class DescribeTest(unittest.TestCase):
    def say(self, expression):
        return cs.describe(cs.parse(expression))

    def test_a_single_time(self):
        self.assertEqual(self.say("0 9 * * *"), "At 09:00")

    def test_weekdays(self):
        self.assertEqual(self.say("0 9 * * 1-5"), "At 09:00, Monday through Friday")

    def test_a_minute_step(self):
        self.assertEqual(self.say("*/15 * * * *"), "Every 15 minutes")

    def test_an_hour_window(self):
        self.assertIn("between 09:00 and 17:59", self.say("*/15 9-17 * * *"))

    def test_an_hour_step_on_the_hour(self):
        self.assertEqual(self.say("0 */6 * * *"), "Every 6 hours, on the hour")

    def test_an_hour_step_off_the_hour(self):
        self.assertEqual(self.say("30 */4 * * *"), "Every 4 hours, at minute 30")

    def test_days_of_the_month(self):
        self.assertEqual(self.say("0 0 1,15 * *"), "At 00:00, on the 1st and 15th")

    def test_months(self):
        self.assertIn("from June through August", self.say("0 12 * 6-8 *"))

    def test_the_or_rule_is_spelled_out(self):
        said = self.say("0 0 1 * 1")
        self.assertIn("or", said)
        self.assertIn("whichever comes first", said)
        self.assertNotIn("on on", said)

    def test_ordinals_read_correctly(self):
        self.assertEqual([cs.ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 31)],
                         ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th",
                          "21st", "22nd", "31st"])


class NextRunsTest(unittest.TestCase):
    def runs(self, expression, start, count=3):
        return cs.next_runs(cs.parse(expression), start, count)

    def test_the_next_run_is_strictly_after_the_start(self):
        start = dt.datetime(2026, 11, 9, 9, 0)
        self.assertEqual(self.runs("0 9 * * *", start, 1),
                         [dt.datetime(2026, 11, 10, 9, 0)])

    def test_weekday_schedules_skip_the_weekend(self):
        friday = dt.datetime(2026, 11, 13, 10, 0)
        got = self.runs("0 9 * * 1-5", friday, 1)
        self.assertEqual(got[0], dt.datetime(2026, 11, 16, 9, 0))  # dushanba

    def test_steps_land_where_they_should(self):
        start = dt.datetime(2026, 11, 9, 9, 1)
        self.assertEqual(self.runs("*/15 * * * *", start, 3),
                         [dt.datetime(2026, 11, 9, 9, 15),
                          dt.datetime(2026, 11, 9, 9, 30),
                          dt.datetime(2026, 11, 9, 9, 45)])

    def test_the_or_rule_fires_on_both(self):
        """0 0 1 * 1 -- har oyning 1-sanasi VA har dushanba.

        Cron'ning eng mashhur tuzog'i: ikkala maydon ham cheklangan bo'lsa,
        ular VA emas, YOKI bilan ishlaydi.
        """
        start = dt.datetime(2026, 11, 26, 0, 0)   # payshanba
        got = self.runs("0 0 1 * 1", start, 3)
        self.assertEqual(got, [dt.datetime(2026, 11, 30, 0, 0),   # dushanba
                               dt.datetime(2026, 12, 1, 0, 0),    # 1-sana
                               dt.datetime(2026, 12, 7, 0, 0)])   # dushanba

    def test_a_restricted_day_of_month_alone_is_an_and(self):
        start = dt.datetime(2026, 11, 2, 0, 0)
        self.assertEqual(self.runs("0 0 15 * *", start, 2),
                         [dt.datetime(2026, 11, 15, 0, 0),
                          dt.datetime(2026, 12, 15, 0, 0)])

    def test_a_date_that_never_happens_returns_nothing(self):
        self.assertEqual(self.runs("0 0 30 2 *", dt.datetime(2026, 1, 1), 1), [])

    def test_february_29_only_lands_on_leap_years(self):
        got = self.runs("0 0 29 2 *", dt.datetime(2026, 3, 1), 2)
        self.assertEqual([d.year for d in got], [2028, 2032])


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, SCRIPT, *args],
                              capture_output=True, text=True)

    def test_it_prints_the_description_and_the_next_runs(self):
        out = self.run_cli("0 9 * * 1-5")
        self.assertEqual(out.returncode, 0)
        self.assertIn("At 09:00, Monday through Friday", out.stdout)
        self.assertIn("next:", out.stdout)

    def test_next_zero_hides_the_schedule(self):
        out = self.run_cli("0 9 * * *", "--next", "0")
        self.assertNotIn("next:", out.stdout)

    def test_an_unquoted_expression_still_works(self):
        out = self.run_cli("0", "9", "*", "*", "*")
        self.assertIn("At 09:00", out.stdout)

    def test_a_bad_expression_exits_two(self):
        out = self.run_cli("not a cron line")
        self.assertEqual(out.returncode, 2)
        self.assertIn("error", out.stderr)

    def test_an_impossible_date_says_never(self):
        out = self.run_cli("0 0 30 2 *")
        self.assertIn("never", out.stdout)


if __name__ == "__main__":
    unittest.main()
