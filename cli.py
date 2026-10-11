"""Command-line entry point: orchestrates fetch -> render -> inject."""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
from collections.abc import Sequence
from pathlib import Path

from . import contributions, languages, projects, render
from .config import ConfigError, load_profile
from .github import GitHub, GitHubError, HttpClient, UrllibClient
from .models import Profile
from .readme import MarkerError, apply_blocks

log = logging.getLogger("profile_readme")


def static_blocks(profile: Profile) -> dict[str, str]:
    return {
        "skills": render.skills(profile.skills),
        "experience": render.experience(profile.experience),
        "credentials": render.credentials(profile.credentials, profile.education),
    }


def live_blocks(profile: Profile, gh: GitHub, today: dt.date) -> tuple[dict[str, str], list[str]]:
    """Fetch GitHub data. Each source fails independently so one outage never blanks the README."""
    blocks: dict[str, str] = {}
    failures: list[str] = []

    try:
        repos = [r for r in gh.repos() if r.name not in profile.settings.exclude]
        sizes = {r.name: gh.languages(r) for r in repos}  # one request per repo, reused below
        selected = projects.select_projects(repos, profile.settings)
        blocks["projects"] = render.projects(selected, profile.settings.descriptions, sizes)
        blocks["languages"] = render.languages(languages.aggregate(sizes.values()), len(repos))
    except GitHubError as exc:
        failures.append(f"projects/languages: {exc}")

    try:
        days = contributions.parse_calendar(gh.contributions_html())
        if not days:
            raise GitHubError("contribution calendar returned no days")
        summary = contributions.summarize(days, gh.commit_count(), today)
        blocks["activity"] = render.activity(summary)
    except GitHubError as exc:
        failures.append(f"activity: {exc}")

    return blocks, failures


def main(
    argv: Sequence[str] | None = None,
    *,
    client: HttpClient | None = None,
    today: dt.date | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="profile_readme", description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("profile.toml"))
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument("--check", action="store_true", help="exit 1 if README is out of date; write nothing")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        profile = load_profile(args.config)
        original = args.readme.read_text(encoding="utf-8")
    except (ConfigError, OSError) as exc:
        log.error("%s", exc)
        return 2

    gh = GitHub(client or UrllibClient(os.environ.get("GITHUB_TOKEN")), profile.settings.user)
    live, failures = live_blocks(profile, gh, today or dt.datetime.now(dt.UTC).date())
    try:
        updated = apply_blocks(original, {**static_blocks(profile), **live})
    except MarkerError as exc:
        log.error("%s", exc)
        return 2

    for failure in failures:
        log.error("kept previous content for %s", failure)
    changed = updated != original
    if args.check:
        log.info("README is %s", "OUT OF DATE" if changed else "up to date")
        return 1 if changed or failures else 0
    if changed:
        args.readme.write_text(updated, encoding="utf-8")
        log.info("README updated")
    else:
        log.info("README already up to date")
    return 1 if failures else 0
