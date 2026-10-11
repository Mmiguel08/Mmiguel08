"""GitHub access behind a small, injectable HTTP interface (easy to fake in tests)."""

from __future__ import annotations

import datetime as dt
import json
import logging
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, Protocol
from urllib.parse import urlparse

from .models import Repo

log = logging.getLogger(__name__)
API_HOST = "api.github.com"


class GitHubError(RuntimeError):
    """Any failure talking to GitHub."""


class HttpClient(Protocol):
    def get(self, url: str, *, accept: str) -> str: ...


class UrllibClient:
    """stdlib HTTP client with retry + exponential backoff on transient failures.

    The token is only ever sent to api.github.com, never to other hosts.
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        retries: int = 3,
        backoff: float = 1.0,
        timeout: float = 30.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._token, self._retries, self._backoff = token, retries, backoff
        self._timeout, self._sleep = timeout, sleep

    def get(self, url: str, *, accept: str = "application/vnd.github+json") -> str:
        headers = {"User-Agent": "profile-readme", "Accept": accept}
        if self._token and urlparse(url).hostname == API_HOST:
            headers["Authorization"] = f"Bearer {self._token}"
        last: Exception | None = None
        for attempt in range(self._retries):
            try:
                request = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(request, timeout=self._timeout) as resp:
                    return str(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code < 500:  # client errors (incl. rate limit) will not fix themselves
                    raise GitHubError(f"HTTP {exc.code} for {url}") from exc
                last = exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last = exc
            if attempt < self._retries - 1:
                delay = self._backoff * 2**attempt
                log.warning("transient error on %s (%s); retrying in %.1fs", url, last, delay)
                self._sleep(delay)
        raise GitHubError(f"giving up on {url}: {last}")


class GitHub:
    """Typed gateway over the few GitHub endpoints this project needs."""

    def __init__(self, client: HttpClient, user: str) -> None:
        self._client, self._user = client, user

    def _json(self, url: str) -> Any:
        try:
            return json.loads(self._client.get(url, accept="application/vnd.github+json"))
        except json.JSONDecodeError as exc:
            raise GitHubError(f"invalid JSON from {url}") from exc

    def repos(self) -> list[Repo]:
        """Public, non-fork, non-archived repositories owned by the user."""
        url = f"https://{API_HOST}/users/{self._user}/repos?per_page=100&type=owner&sort=pushed"
        payload = self._json(url)
        if not isinstance(payload, list):
            raise GitHubError(f"unexpected repos payload: {str(payload)[:120]}")
        return [
            Repo(
                name=r["name"],
                url=r["html_url"],
                description=r.get("description"),
                language=r.get("language"),
                stars=int(r.get("stargazers_count", 0)),
                pushed_at=dt.datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00")),
                topics=tuple(r.get("topics", ())),
                languages_url=r["languages_url"],
            )
            for r in payload
            if not r.get("fork") and not r.get("archived")
        ]

    def languages(self, repo: Repo) -> dict[str, int]:
        data = self._json(repo.languages_url)
        return {str(k): int(v) for k, v in data.items()}

    def commit_count(self) -> int | None:
        """Total public commits authored; None if the search API is unavailable."""
        try:
            data = self._json(f"https://{API_HOST}/search/commits?q=author:{self._user}&per_page=1")
            return int(data["total_count"])
        except (GitHubError, KeyError, TypeError, ValueError) as exc:
            log.warning("commit count unavailable: %s", exc)
            return None

    def contributions_html(self) -> str:
        return self._client.get(f"https://github.com/users/{self._user}/contributions", accept="text/html")
