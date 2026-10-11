"""Immutable domain models. No I/O and no formatting live here."""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SkillGroup:
    domain: str
    items: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Role:
    title: str
    company: str
    location: str
    period: str
    highlights: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Credential:
    name: str
    issuer: str
    year: int
    url: str | None = None


@dataclass(frozen=True, slots=True)
class Education:
    degree: str
    institution: str
    period: str
    status: str


@dataclass(frozen=True, slots=True)
class Settings:
    user: str
    max_projects: int
    exclude: frozenset[str]
    descriptions: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class Profile:
    settings: Settings
    skills: tuple[SkillGroup, ...]
    experience: tuple[Role, ...]
    credentials: tuple[Credential, ...]
    education: Education


@dataclass(frozen=True, slots=True)
class Repo:
    name: str
    url: str
    description: str | None
    language: str | None
    stars: int
    pushed_at: dt.datetime
    topics: tuple[str, ...]
    languages_url: str


@dataclass(frozen=True, slots=True)
class LanguageStat:
    name: str
    size: int
    share: float  # 0.0 - 1.0


@dataclass(frozen=True, slots=True)
class ContributionDay:
    date: dt.date
    count: int
    level: int  # 0-4, as classified by GitHub


@dataclass(frozen=True, slots=True)
class ActivitySummary:
    days: tuple[ContributionDay, ...]
    total_12_months: int
    commits: int | None
    current_streak: int
    longest_streak: int
    monthly: tuple[tuple[dt.date, int], ...]  # first day of month -> contributions
