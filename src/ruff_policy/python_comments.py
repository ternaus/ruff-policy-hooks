"""Read Ruff suppression comments from Python source."""

from __future__ import annotations

import re
import tokenize
from dataclasses import dataclass
from pathlib import Path

from .selectors import parse_selectors

_NOQA_PATTERN = re.compile(r"#\s*(?:ruff:\s*)?noqa\b(?P<rest>.*)$", re.IGNORECASE)
_SELECTOR_PATTERN = re.compile(r"[A-Za-z]+[0-9]*")


@dataclass(frozen=True)
class Suppression:
    """A Ruff suppression comment and its source location."""

    line: int
    selectors: tuple[str, ...] | None


def _parse_selectors(rest: str) -> tuple[str, ...] | None:
    """Parse the selector list after ``noqa``; ``None`` means blanket noqa."""
    rest = rest.strip()
    if not rest.startswith(":"):
        return None

    selector_text = rest[1:].split("#", 1)[0].split("-", 1)[0]
    selectors = parse_selectors(_SELECTOR_PATTERN.findall(selector_text))
    return selectors or None


def iter_suppressions(path: Path) -> list[Suppression]:
    """Return all Ruff suppression comments in *path*."""
    suppressions: list[Suppression] = []
    with tokenize.open(path) as source:
        tokens = tokenize.generate_tokens(source.readline)
        for token in tokens:
            if token.type != tokenize.COMMENT:
                continue
            match = _NOQA_PATTERN.search(token.string)
            if match is None:
                continue
            suppressions.append(Suppression(token.start[0], _parse_selectors(match.group("rest"))))
    return suppressions
