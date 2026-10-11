"""Project selection policy."""

from __future__ import annotations

from collections.abc import Iterable

from .models import Repo, Settings

FEATURED_TOPIC = "featured"


def select_projects(repos: Iterable[Repo], settings: Settings) -> list[Repo]:
    """Featured repos first (topic `featured`), then most recently pushed; capped."""
    eligible = [r for r in repos if r.name not in settings.exclude]
    eligible.sort(key=lambda r: r.pushed_at, reverse=True)
    featured = [r for r in eligible if FEATURED_TOPIC in r.topics]
    others = [r for r in eligible if FEATURED_TOPIC not in r.topics]
    return (featured + others)[: settings.max_projects]
