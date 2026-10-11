import datetime as dt
import re
import unittest

from profile_readme import contributions, languages, render
from profile_readme.models import ContributionDay, Credential, Education, LanguageStat, Repo, Role, SkillGroup

from .helpers import CALENDAR_HTML


def repo(
    name: str = "r",
    description: str | None = "d",
    language: str | None = "HCL",
    stars: int = 1,
) -> Repo:
    return Repo(
        name=name,
        url="https://x/r",
        description=description,
        language=language,
        stars=stars,
        pushed_at=dt.datetime(2026, 10, 10, tzinfo=dt.UTC),
        topics=(),
        languages_url="u",
    )


class RenderTests(unittest.TestCase):
    def test_skills_table_escapes_pipes(self) -> None:
        out = render.skills([SkillGroup("Net|work", ("BGP", "OSPF"))])
        self.assertIn("**Net\\|work**", out)
        self.assertIn("`BGP` · `OSPF`", out)

    def test_experience_has_headline_and_bullets(self) -> None:
        out = render.experience([Role("Eng", "Acme", "Remote", "2024", ("did x",))])
        self.assertIn("**Eng** — Acme, Remote · *2024*", out)
        self.assertIn("- did x", out)

    def test_credentials_sorted_newest_first_and_linked(self) -> None:
        items = [Credential("Old", "A", 2020), Credential("New", "B", 2026, "https://v")]
        out = render.credentials(items, Education("Deg", "Uni", "2024 – 2028", "in progress"))
        self.assertLess(out.index("New"), out.index("Old"))
        self.assertIn("[New](https://v)", out)
        self.assertIn("in progress", out)

    def test_projects_prefers_override_then_description(self) -> None:
        out = render.projects([repo(name="a", description="from gh")], {"a": "override"})
        self.assertIn("override", out)
        self.assertNotIn("from gh", out)
        self.assertIn("Oct 10, 2026", out)

    def test_projects_show_every_language_with_share(self) -> None:
        out = render.projects([repo(name="a")], {}, {"a": {"HCL": 750, "Shell": 250}})
        self.assertIn("`HCL (Terraform)` 75% · `Shell (Bash)` 25%", out)

    def test_projects_fall_back_to_primary_language_without_sizes(self) -> None:
        self.assertIn("`HCL (Terraform)`", render.projects([repo(name="a")], {}, {}))

    def test_projects_without_any_language(self) -> None:
        out = render.projects([repo(name="a", language=None)], {}, {"a": {}})
        self.assertIn("| — |", out)

    def test_language_mix_edge_cases(self) -> None:
        self.assertEqual(render.language_mix({"Shell": 100}), "`Shell (Bash)` 100%")
        self.assertIn("`Go` <1%", render.language_mix({"Python": 10_000, "Go": 5}))
        many = {"A": 50, "B": 40, "C": 30, "D": 20, "E": 10}
        self.assertTrue(render.language_mix(many).endswith("+2"))  # top 3 shown, rest summarized

    def test_projects_empty_state(self) -> None:
        self.assertIn("No public repositories", render.projects([], {}))

    def test_bar_bounds(self) -> None:
        self.assertEqual(render.bar(0.0), "░" * render.BAR_WIDTH)
        self.assertEqual(render.bar(1.0), "█" * render.BAR_WIDTH)
        self.assertEqual(render.bar(0.001).count("█"), 1)  # never invisible

    def test_languages_block(self) -> None:
        out = render.languages([LanguageStat("HCL", 2048, 1.0)], 1)
        self.assertIn("HCL (Terraform)", out)
        self.assertIn("100.0%", out)
        self.assertIn("1 public repository;", out)

    def test_languages_empty_state(self) -> None:
        self.assertIn("No language data", render.languages([], 2))

    def test_activity_contains_kpis_heatmap_and_trend(self) -> None:
        days = contributions.parse_calendar(CALENDAR_HTML)
        summary = contributions.summarize(days, 43, dt.date(2026, 10, 3))
        out = render.activity(summary)
        self.assertIn("| **18** | **43** |", out)
        self.assertIn("Mon", out)
        self.assertIn("Trend", out)
        self.assertTrue(any(ch in out for ch in "░▒▓█"))

    def test_activity_without_days_renders_only_kpis(self) -> None:
        summary = contributions.summarize([], None, dt.date(2026, 10, 3))
        out = render.activity(summary)
        self.assertIn("n/a", out)
        self.assertNotIn("```", out)


class HeatmapTests(unittest.TestCase):
    def test_every_month_gets_a_separate_label(self) -> None:
        start = dt.date(2025, 10, 12)
        year = [ContributionDay(start + dt.timedelta(days=i), 1, 1) for i in range(365)]
        header = render._heatmap(year)[0]
        labels = re.findall(r"[A-Z][a-z]{2}", header)
        self.assertIn("Nov", labels)  # regression: used to be skipped by an off-by-one
        self.assertGreaterEqual(len(labels), 11)
        self.assertNotRegex(header, r"[A-Za-z]{4,}")  # labels never touch each other

    def test_grid_is_seven_rows_plus_header_and_legend(self) -> None:
        days = contributions.parse_calendar(CALENDAR_HTML)
        self.assertEqual(len(render._heatmap(days)), 1 + 7 + 1)


class AggregateTests(unittest.TestCase):
    def test_folds_tail_into_other(self) -> None:
        stats = languages.aggregate([{"A": 50, "B": 30, "C": 15, "D": 5}], top=2)
        self.assertEqual([s.name for s in stats], ["A", "B", languages.OTHER])
        self.assertAlmostEqual(sum(s.share for s in stats), 1.0)

    def test_empty_and_zero(self) -> None:
        self.assertEqual(languages.aggregate([]), [])
        self.assertEqual(languages.aggregate([{}]), [])


if __name__ == "__main__":
    unittest.main()
