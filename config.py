"""Loads and validates profile.toml, failing early with actionable messages."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypeVar

from .models import Credential, Education, Profile, Role, Settings, SkillGroup

T = TypeVar("T")


class ConfigError(ValueError):
    """Raised when profile.toml is missing a field or has the wrong type."""


def _get(table: Mapping[str, Any], key: str, expected: type[T], where: str) -> T:
    if key not in table:
        raise ConfigError(f"{where}: missing required key '{key}'")
    value = table[key]
    if not isinstance(value, expected):
        raise ConfigError(f"{where}.{key}: expected {expected.__name__}, got {type(value).__name__}")
    return value


def _strings(table: Mapping[str, Any], key: str, where: str) -> tuple[str, ...]:
    values = _get(table, key, list, where)
    if not all(isinstance(v, str) for v in values):
        raise ConfigError(f"{where}.{key}: all items must be strings")
    return tuple(values)


def _tables(raw: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    return _get(raw, key, list, "profile")


def parse_profile(raw: Mapping[str, Any]) -> Profile:
    github = _get(raw, "github", dict, "profile")
    projects = raw.get("projects", {})
    settings = Settings(
        user=_get(github, "user", str, "github"),
        max_projects=_get(github, "max_projects", int, "github"),
        exclude=frozenset(_strings(github, "exclude", "github")),
        descriptions=dict(projects.get("descriptions", {})),
    )
    if settings.max_projects < 1:
        raise ConfigError("github.max_projects: must be >= 1")

    skills = tuple(
        SkillGroup(_get(t, "domain", str, "skills"), _strings(t, "items", "skills"))
        for t in _tables(raw, "skills")
    )
    experience = tuple(
        Role(
            title=_get(t, "title", str, "experience"),
            company=_get(t, "company", str, "experience"),
            location=_get(t, "location", str, "experience"),
            period=_get(t, "period", str, "experience"),
            highlights=_strings(t, "highlights", "experience"),
        )
        for t in _tables(raw, "experience")
    )
    credentials = tuple(
        Credential(
            name=_get(t, "name", str, "credentials"),
            issuer=_get(t, "issuer", str, "credentials"),
            year=_get(t, "year", int, "credentials"),
            url=t.get("url"),
        )
        for t in _tables(raw, "credentials")
    )
    edu = _get(raw, "education", dict, "profile")
    education = Education(
        degree=_get(edu, "degree", str, "education"),
        institution=_get(edu, "institution", str, "education"),
        period=_get(edu, "period", str, "education"),
        status=_get(edu, "status", str, "education"),
    )
    return Profile(settings, skills, experience, credentials, education)


def load_profile(path: Path) -> Profile:
    try:
        with path.open("rb") as fh:
            return parse_profile(tomllib.load(fh))
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc
