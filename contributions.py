"""Pure functions: parse GitHub's contribution calendar and derive statistics."""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterable, Sequence

from .models import ActivitySummary, ContributionDay

_TD = re.compile(r"<td\b[^>]*>")
_DATE = re.compile(r'data-date="(\d{4}-\d{2}-\d{2})"')
_ID = re.compile(r'id="(contribution-day-component-[\d-]+)"')
_LEVEL = re.compile(r'data-level="(\d)"')
_TOOLTIP = re.compile(r'for="(contribution-day-component-[\d-]+)"[^>]*>\s*([^<]*)')
_COUNT = re.compile(r"^(\d+) contribution")


def parse_calendar(html: str) -> list[ContributionDay]:
    """Extract one ContributionDay per calendar cell, sorted by date."""
    tooltips = {m.group(1): m.group(2).strip() for m in _TOOLTIP.finditer(html)}
    days: dict[dt.date, ContributionDay] = {}
    for tag in _TD.findall(html):
        date_m, level_m, id_m = _DATE.search(tag), _LEVEL.search(tag), _ID.search(tag)
        if not date_m:
            continue
        level = int(level_m.group(1)) if level_m else 0
        count_m = _COUNT.match(tooltips.get(id_m.group(1), "")) if id_m else None
        count = int(count_m.group(1)) if count_m else 0
        # If a tooltip is missing but GitHub colored the cell, the day was not empty.
        count = max(count, 1 if level else 0)
        date = dt.date.fromisoformat(date_m.group(1))
        days[date] = ContributionDay(date, count, level)
    return [days[d] for d in sorted(days)]


def streaks(days: Sequence[ContributionDay]) -> tuple[int, int]:
    """Return (current, longest) streak of consecutive active days.

    The current streak survives an empty *today*, since the day is not over yet.
    """
    longest = run = 0
    for day in days:
        run = run + 1 if day.count else 0
        longest = max(longest, run)

    trimmed = list(days[:-1] if days and days[-1].count == 0 else days)
    current = 0
    for day in reversed(trimmed):
        if not day.count:
            break
        current += 1
    return current, longest


def _month_start(year: int, month: int) -> dt.date:
    return dt.date(year, month, 1)


def last_twelve_months(today: dt.date) -> list[dt.date]:
    """First day of each of the 12 calendar months ending with today's month."""
    months: list[dt.date] = []
    year, month = today.year, today.month
    for _ in range(12):
        months.append(_month_start(year, month))
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return months[::-1]


def monthly_totals(days: Iterable[ContributionDay], today: dt.date) -> tuple[tuple[dt.date, int], ...]:
    totals = dict.fromkeys(last_twelve_months(today), 0)
    for day in days:
        key = _month_start(day.date.year, day.date.month)
        if key in totals:
            totals[key] += day.count
    return tuple(totals.items())


def summarize(days: Sequence[ContributionDay], commits: int | None, today: dt.date) -> ActivitySummary:
    window_start = today - dt.timedelta(days=365)
    current, longest = streaks(days)
    return ActivitySummary(
        days=tuple(days),
        total_12_months=sum(d.count for d in days if d.date > window_start),
        commits=commits,
        current_streak=current,
        longest_streak=longest,
        monthly=monthly_totals(days, today),
    )
