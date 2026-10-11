"""Idempotent replacement of generated blocks delimited by HTML comment markers."""

from __future__ import annotations

import re
from collections.abc import Mapping


class MarkerError(LookupError):
    """A required BEGIN/END marker pair is missing from the README."""


def _pattern(name: str) -> re.Pattern[str]:
    return re.compile(
        rf"(<!-- BEGIN:{re.escape(name)} -->)\n?.*?\n?(<!-- END:{re.escape(name)} -->)", re.DOTALL
    )


def replace_block(text: str, name: str, content: str) -> str:
    pattern = _pattern(name)
    if not pattern.search(text):
        raise MarkerError(f"missing markers for block '{name}' (<!-- BEGIN:{name} --> / <!-- END:{name} -->)")
    return pattern.sub(lambda m: f"{m.group(1)}\n{content.strip()}\n{m.group(2)}", text, count=1)


def apply_blocks(text: str, blocks: Mapping[str, str]) -> str:
    for name, content in blocks.items():
        text = replace_block(text, name, content)
    return text
