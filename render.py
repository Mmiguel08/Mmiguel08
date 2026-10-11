"""Pure renderers: domain objects in, Markdown out. No I/O, no clock, no network."""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence

from .models import (
    ActivitySummary,
    ContributionDay,
    Credential,
    Education,
    LanguageStat,
    Repo,
    Role,
    SkillGroup,
)

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
HEAT = ("·", "░", "▒", "▓", "█")
SPARK = "▁▂▃▄▅▆▇█"
LANGUAGE_LABELS = {"HCL": "HCL (Terraform)", "Shell": "Shell (Bash)"}
BAR_WIDTH = 24


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _fmt_date(d: dt.date) -> str:
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _fence(lines: Sequence[str]) -> str:
    return "```text\n" + "\n".join(line.rstrip() for line in lines) + "\n```"


def skills(groups: Sequence[SkillGroup]) -> str:
    rows = ["| Domain | Stack |", "|---|---|"]
    for g in groups:
        stack = " · ".join(f"`{_cell(i)}`" for i in g.items)
        rows.append(f"| **{_cell(g.domain)}** | {stack} |")
    return "\n".join(rows)


def experience(roles: Sequence[Role]) -> str:
    blocks = []
    for r in roles:
        head = f"**{r.title}** — {r.company}, {r.location} · *{r.period}*"
        bullets = "\n".join(f"- {h}" for h in r.highlights)
        blocks.append(f"{head}\n\n{bullets}")
    return "\n\n".join(blocks)


def credentials(items: Sequence[Credential], education: Education) -> str:
    rows = ["| Credential | Issuer | Year |", "|---|---|---:|"]
    for c in sorted(items, key=lambda c: c.year, reverse=True):
        name = f"[{_cell(c.name)}]({c.url})" if c.url else _cell(c.name)
        rows.append(f"| {name} | {_cell(c.issuer)} | {c.year} |")
    edu = (
        f"**Education** — {education.degree}, {education.institution} "
        f"· *{education.period} ({education.status})*"
    )
    return "\n".join(rows) + "\n\n" + edu


def language_mix(sizes: Mapping[str, int], fallback: str | None = None, top: int = 3) -> str:
    """e.g. `HCL (Terraform)` 87% · `Shell` 13%. Falls back to GitHub's primary language."""
    total = sum(sizes.values())
    if total == 0:
        return f"`{LANGUAGE_LABELS.get(fallback, fallback)}`" if fallback else "—"
    ranked = sorted(sizes.items(), key=lambda kv: kv[1], reverse=True)

    def pct(size: int) -> str:
        share = size / total * 100
        return "<1%" if share < 1 else f"{share:.0f}%"

    parts = [f"`{LANGUAGE_LABELS.get(name, name)}` {pct(size)}" for name, size in ranked[:top]]
    if len(ranked) > top:
        parts.append(f"+{len(ranked) - top}")
    return " · ".join(parts)


def projects(
    repos: Sequence[Repo],
    descriptions: Mapping[str, str],
    languages: Mapping[str, Mapping[str, int]] | None = None,
) -> str:
    if not repos:
        return "*No public repositories yet.*"
    languages = languages or {}
    rows = ["| Project | Description | Languages | Stars | Updated |", "|---|---|---|---:|---|"]
    for r in repos:
        desc = descriptions.get(r.name) or r.description or "—"
        mix = language_mix(languages.get(r.name, {}), r.language)
        rows.append(
            f"| [**{_cell(r.name)}**]({r.url}) | {_cell(desc)} | {mix} | {r.stars} "
            f"| {_fmt_date(r.pushed_at.date())} |"
        )
    return "\n".join(rows)


def bar(share: float, width: int = BAR_WIDTH) -> str:
    filled = min(width, max(1, round(share * width))) if share > 0 else 0
    return "█" * filled + "░" * (width - filled)


def languages(stats: Sequence[LanguageStat], repo_count: int) -> str:
    if not stats:
        return "*No language data detected yet; it appears as repositories gain code.*"
    labels = [LANGUAGE_LABELS.get(s.name, s.name) for s in stats]
    pad = max(map(len, labels))
    lines = [
        f"{label:<{pad}}  {bar(s.share)}  {s.share * 100:5.1f}%  {s.size / 1024:8.1f} KB"
        for label, s in zip(labels, stats, strict=True)
    ]
    noun = "repository" if repo_count == 1 else "repositories"
    note = f"*By bytes of code across {repo_count} public {noun}; forks excluded.*"
    return _fence(lines) + "\n\n" + note


def _heatmap(days: Sequence[ContributionDay]) -> list[str]:
    """GitHub-style grid: 7 rows (Sun-Sat) x one column per week."""
    first = days[0].date
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)  # Sunday on/before first day
    cols = (days[-1].date - start).days // 7 + 1
    grid = [[" "] * cols for _ in range(7)]
    for d in days:
        grid[(d.date.weekday() + 1) % 7][(d.date - start).days // 7] = HEAT[d.level]

    def month_of(col: int) -> int:
        return (start + dt.timedelta(weeks=col)).month

    # A label needs 3 columns: when two month boundaries are closer than that, keep the later one.
    boundaries = [c for c in range(cols) if c == 0 or month_of(c) != month_of(c - 1)]
    kept = [c for i, c in enumerate(boundaries) if i == len(boundaries) - 1 or boundaries[i + 1] - c >= 4]
    header = [" "] * cols
    for c in kept:
        if c + 3 <= cols:
            header[c : c + 3] = list(MONTHS[month_of(c) - 1])

    names = ("   ", "Mon", "   ", "Wed", "   ", "Fri", "   ")
    lines = ["    " + "".join(header)]
    lines += [f"{names[r]} {''.join(grid[r])}" for r in range(7)]
    lines.append("    Less " + " ".join(HEAT) + " More")
    return lines


def _monthly(monthly: Sequence[tuple[dt.date, int]]) -> list[str]:
    peak = max((v for _, v in monthly), default=0)

    def spark(v: int) -> str:
        return "·" if v == 0 else SPARK[min(len(SPARK) - 1, round(v / peak * (len(SPARK) - 1)))]

    return [
        "Month " + "".join(f"{MONTHS[m.month - 1]:>4}" for m, _ in monthly),
        "Total " + "".join(f"{v:>4}" for _, v in monthly),
        "Trend " + "".join(f"{spark(v):>4}" for _, v in monthly),
    ]


def activity(s: ActivitySummary) -> str:
    commits = f"{s.commits:,}" if s.commits is not None else "n/a"
    table = (
        "| Contributions (12 mo) | Public commits | Current streak | Longest streak |\n"
        "|---:|---:|---:|---:|\n"
        f"| **{s.total_12_months:,}** | **{commits}** | {_plural(s.current_streak, 'day')} "
        f"| {_plural(s.longest_streak, 'day')} |"
    )
    if not s.days:
        return table
    return table + "\n\n" + _fence([*_heatmap(s.days), "", *_monthly(s.monthly)])
