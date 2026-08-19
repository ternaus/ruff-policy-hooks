"""Normalize and compare Ruff rule selectors."""

from __future__ import annotations

import re
from collections.abc import Iterable

_SELECTOR_PATTERN = re.compile(r"[A-Z][A-Z0-9]*")


class SelectorError(ValueError):
    """Raised when a Ruff selector is empty or malformed."""


def normalize_selector(value: str) -> str:
    """Return an uppercase Ruff selector or raise a useful validation error."""
    selector = value.strip().upper()
    if not selector or _SELECTOR_PATTERN.fullmatch(selector) is None:
        raise SelectorError(f"invalid Ruff selector: {value!r}")
    return selector


def parse_selectors(values: Iterable[str]) -> tuple[str, ...]:
    """Parse repeated or comma-separated selector arguments."""
    selectors: list[str] = []
    for value in values:
        for item in value.split(","):
            item = item.strip()
            if not item:
                continue
            selector = normalize_selector(item)
            if selector not in selectors:
                selectors.append(selector)
    return tuple(selectors)


def selector_covers(container: str, candidate: str) -> bool:
    """Return whether *container* selects every rule selected by *candidate*."""
    return container == "ALL" or candidate.startswith(container)


def selectors_intersect(left: str, right: str) -> bool:
    """Return whether two Ruff selectors can select at least one common rule."""
    return left == "ALL" or right == "ALL" or left.startswith(right) or right.startswith(left)


def suppression_hits_forbidden(suppressed: str, forbidden: Iterable[str]) -> bool:
    """Return whether a suppression selector overlaps a forbidden selector."""
    return any(selectors_intersect(suppressed, rule) for rule in forbidden)


def suppression_is_allowed(suppressed: str, allowed: Iterable[str]) -> bool:
    """Return whether an allowlist fully covers a suppression selector."""
    return any(selector_covers(rule, suppressed) for rule in allowed)
