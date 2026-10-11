import datetime as dt
import unittest

from profile_readme import contributions as c
from profile_readme.models import ContributionDay as D

from .helpers import CALENDAR_HTML


def days(*counts: int, start: dt.date = dt.date(2026, 10, 1)) -> list[D]:
    return [D(start + dt.timedelta(days=i), n, min(n, 4)) for i, n in enumerate(counts)]


class ParseCalendarTests(unittest.TestCase):
    def test_parses_dates_counts_and_levels_sorted(self) -> None:
        parsed = c.parse_calendar(CALENDAR_HTML)
        self.assertEqual([d.count for d in parsed], [0, 3, 1, 0, 9, 5, 0])
        self.assertEqual([d.level for d in parsed], [0, 2, 1, 0, 4, 3, 0])
        self.assertEqual(parsed[0].date, dt.date(2026, 9, 27))
        self.assertEqual(parsed, sorted(parsed, key=lambda d: d.date))

    def test_empty_html_yields_no_days(self) -> None:
        self.assertEqual(c.parse_calendar("<html></html>"), [])

    def test_colored_cell_without_tooltip_counts_as_active(self) -> None:
        html = '<td data-date="2026-10-01" id="contribution-day-component-0-0" data-level="2"></td>'
        self.assertEqual(c.parse_calendar(html)[0].count, 1)


class StreakTests(unittest.TestCase):
    def test_longest_and_current(self) -> None:
        self.assertEqual(c.streaks(days(1, 1, 1, 0, 1, 1)), (2, 3))

    def test_current_streak_survives_empty_today(self) -> None:
        self.assertEqual(c.streaks(days(0, 2, 2, 0)), (2, 2))

    def test_no_activity(self) -> None:
        self.assertEqual(c.streaks(days(0, 0, 0)), (0, 0))

    def test_empty_input(self) -> None:
        self.assertEqual(c.streaks([]), (0, 0))


class MonthlyTests(unittest.TestCase):
    def test_twelve_months_ending_current_across_year_boundary(self) -> None:
        months = c.last_twelve_months(dt.date(2026, 2, 15))
        self.assertEqual(len(months), 12)
        self.assertEqual(months[0], dt.date(2025, 3, 1))
        self.assertEqual(months[-1], dt.date(2026, 2, 1))

    def test_totals_ignore_days_outside_window(self) -> None:
        today = dt.date(2026, 10, 11)
        sample = [D(dt.date(2026, 10, 1), 4, 3), D(dt.date(2026, 10, 2), 1, 1), D(dt.date(2024, 1, 1), 99, 4)]
        totals = dict(c.monthly_totals(sample, today))
        self.assertEqual(totals[dt.date(2026, 10, 1)], 5)
        self.assertNotIn(dt.date(2024, 1, 1), totals)

    def test_summarize_counts_only_last_365_days(self) -> None:
        today = dt.date(2026, 10, 11)
        sample = [D(dt.date(2025, 9, 1), 50, 4), D(dt.date(2026, 10, 10), 2, 2), D(today, 3, 3)]
        summary = c.summarize(sample, commits=7, today=today)
        self.assertEqual(summary.total_12_months, 5)
        self.assertEqual(summary.commits, 7)


if __name__ == "__main__":
    unittest.main()
