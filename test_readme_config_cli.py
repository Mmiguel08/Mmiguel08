import datetime as dt
import logging
import tempfile
import unittest
from pathlib import Path

from profile_readme import projects
from profile_readme.cli import main
from profile_readme.config import ConfigError, load_profile, parse_profile
from profile_readme.github import GitHub, GitHubError, UrllibClient
from profile_readme.models import Settings
from profile_readme.readme import MarkerError, apply_blocks, replace_block

from .helpers import FakeClient, default_routes

ROOT = Path(__file__).resolve().parent.parent
BLOCKS = ("skills", "experience", "credentials", "projects", "languages", "activity")
README = "# Hi\n\n" + "\n".join(f"<!-- BEGIN:{b} -->\nold\n<!-- END:{b} -->" for b in BLOCKS) + "\n"


class MarkerTests(unittest.TestCase):
    def test_replace_is_idempotent(self) -> None:
        once = replace_block(README, "skills", "NEW")
        self.assertEqual(replace_block(once, "skills", "NEW"), once)
        self.assertIn("<!-- BEGIN:skills -->\nNEW\n<!-- END:skills -->", once)

    def test_other_blocks_untouched(self) -> None:
        self.assertIn("old", replace_block(README, "skills", "NEW"))

    def test_missing_marker_raises(self) -> None:
        with self.assertRaises(MarkerError):
            replace_block("no markers", "skills", "x")

    def test_apply_blocks(self) -> None:
        out = apply_blocks(README, {"skills": "A", "activity": "B"})
        self.assertIn("\nA\n", out)
        self.assertIn("\nB\n", out)


class ConfigTests(unittest.TestCase):
    def test_shipped_profile_is_valid(self) -> None:
        profile = load_profile(ROOT / "profile.toml")
        self.assertTrue(profile.skills and profile.experience and profile.credentials)

    def test_missing_key_is_reported_with_location(self) -> None:
        with self.assertRaisesRegex(ConfigError, "github: missing required key 'user'"):
            parse_profile({"github": {}})

    def test_missing_file(self) -> None:
        with self.assertRaises(ConfigError):
            load_profile(Path("/nonexistent/profile.toml"))


class SelectionTests(unittest.TestCase):
    def test_featured_first_then_recent_and_exclusions(self) -> None:
        repos = GitHub(FakeClient(default_routes()), "u").repos()
        settings = Settings("u", 3, frozenset({"u"}), {})
        names = [r.name for r in projects.select_projects(repos, settings)]
        self.assertEqual(names, ["beta", "alpha"])  # featured first; fork and profile repo gone


class RetryTests(unittest.TestCase):
    def test_gives_up_after_retries_without_real_network(self) -> None:
        sleeps: list[float] = []
        client = UrllibClient(retries=3, backoff=0.5, timeout=0.2, sleep=sleeps.append)
        with self.assertLogs("profile_readme.github", level="WARNING"), self.assertRaises(GitHubError):
            client.get("http://127.0.0.1:9/unreachable", accept="text/html")
        self.assertEqual(sleeps, [0.5, 1.0])  # exponential backoff between attempts


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.readme = Path(self.tmp.name) / "README.md"
        self.readme.write_text(README, encoding="utf-8")
        (Path(self.tmp.name) / "profile.toml").write_text(
            (ROOT / "profile.toml").read_text(encoding="utf-8").replace("Mmiguel08", "u"), encoding="utf-8"
        )
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def run_cli(self, routes: dict[str, str], *extra: str) -> int:
        argv = ["--config", str(Path(self.tmp.name) / "profile.toml"), "--readme", str(self.readme), *extra]
        return main(argv, client=FakeClient(routes), today=dt.date(2026, 10, 3))

    def test_end_to_end_updates_every_block(self) -> None:
        self.assertEqual(self.run_cli(default_routes()), 0)
        text = self.readme.read_text(encoding="utf-8")
        self.assertNotIn("\nold\n", text)
        self.assertIn("[**beta**](https://github.com/u/beta)", text)
        self.assertIn("Python", text)
        self.assertIn("| **18** | **43** |", text)

    def test_second_run_is_a_no_op_and_check_passes(self) -> None:
        self.run_cli(default_routes())
        first = self.readme.read_text(encoding="utf-8")
        self.assertEqual(self.run_cli(default_routes(), "--check"), 0)
        self.assertEqual(self.readme.read_text(encoding="utf-8"), first)

    def test_check_flags_stale_readme_without_writing(self) -> None:
        self.assertEqual(self.run_cli(default_routes(), "--check"), 1)
        self.assertEqual(self.readme.read_text(encoding="utf-8"), README)

    def test_github_outage_keeps_old_live_blocks_and_fails_visibly(self) -> None:
        self.assertEqual(self.run_cli({}), 1)
        text = self.readme.read_text(encoding="utf-8")
        self.assertIn("<!-- BEGIN:projects -->\nold\n<!-- END:projects -->", text)
        self.assertIn("`Terraform`", text)  # static blocks still refreshed

    def test_missing_markers_is_a_config_error(self) -> None:
        self.readme.write_text("no markers here", encoding="utf-8")
        self.assertEqual(self.run_cli(default_routes()), 2)


if __name__ == "__main__":
    unittest.main()
