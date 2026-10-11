"""Shared fixtures and a fake HTTP client (no network in tests)."""

from __future__ import annotations

import json

from profile_readme.github import GitHubError

CALENDAR_HTML = """
<td data-date="2026-09-27" id="contribution-day-component-0-0" data-level="0" class="d"></td>
<td data-date="2026-09-28" id="contribution-day-component-1-0" data-level="2" class="d"></td>
<td data-date="2026-09-29" id="contribution-day-component-2-0" data-level="1" class="d"></td>
<td data-date="2026-09-30" id="contribution-day-component-3-0" data-level="0" class="d"></td>
<td data-date="2026-10-01" id="contribution-day-component-4-0" data-level="4" class="d"></td>
<td data-date="2026-10-02" id="contribution-day-component-5-0" data-level="3" class="d"></td>
<td data-date="2026-10-03" id="contribution-day-component-6-0" data-level="0" class="d"></td>
<tool-tip for="contribution-day-component-0-0" class="sr-only">No contributions on September 27th.</tool-tip>
<tool-tip for="contribution-day-component-1-0" class="sr-only">3 contributions on September 28th.</tool-tip>
<tool-tip for="contribution-day-component-2-0" class="sr-only">1 contribution on September 29th.</tool-tip>
<tool-tip for="contribution-day-component-3-0" class="sr-only">No contributions on September 30th.</tool-tip>
<tool-tip for="contribution-day-component-4-0" class="sr-only">9 contributions on October 1st.</tool-tip>
<tool-tip for="contribution-day-component-5-0" class="sr-only">5 contributions on October 2nd.</tool-tip>
<tool-tip for="contribution-day-component-6-0" class="sr-only">No contributions on October 3rd.</tool-tip>
"""

REPOS_JSON = json.dumps(
    [
        {
            "name": "alpha",
            "html_url": "https://github.com/u/alpha",
            "description": "Alpha repo",
            "language": "HCL",
            "stargazers_count": 2,
            "pushed_at": "2026-10-01T10:00:00Z",
            "topics": [],
            "fork": False,
            "archived": False,
            "languages_url": "https://api.github.com/r/alpha/languages",
        },
        {
            "name": "beta",
            "html_url": "https://github.com/u/beta",
            "description": None,
            "language": None,
            "stargazers_count": 0,
            "pushed_at": "2026-10-05T10:00:00Z",
            "topics": ["featured"],
            "fork": False,
            "archived": False,
            "languages_url": "https://api.github.com/r/beta/languages",
        },
        {
            "name": "forked",
            "html_url": "https://github.com/u/forked",
            "description": None,
            "language": "Go",
            "stargazers_count": 0,
            "pushed_at": "2026-10-06T10:00:00Z",
            "topics": [],
            "fork": True,
            "archived": False,
            "languages_url": "https://api.github.com/r/forked/languages",
        },
        {
            "name": "u",
            "html_url": "https://github.com/u/u",
            "description": None,
            "language": None,
            "stargazers_count": 0,
            "pushed_at": "2026-10-07T10:00:00Z",
            "topics": [],
            "fork": False,
            "archived": False,
            "languages_url": "https://api.github.com/r/u/languages",
        },
    ]
)


class FakeClient:
    """Maps URL substrings to canned responses; unknown URLs raise like a 404."""

    def __init__(self, routes: dict[str, str]) -> None:
        self.routes, self.calls = routes, []

    def get(self, url: str, *, accept: str) -> str:
        self.calls.append(url)
        for fragment, body in self.routes.items():
            if fragment in url:
                return body
        raise GitHubError(f"HTTP 404 for {url}")


def default_routes() -> dict[str, str]:
    return {
        "/users/u/repos": REPOS_JSON,
        "/r/alpha/languages": json.dumps({"HCL": 3000, "Shell": 1000}),
        "/r/beta/languages": json.dumps({"Python": 6000}),
        "/search/commits": json.dumps({"total_count": 43}),
        "/users/u/contributions": CALENDAR_HTML,
    }
