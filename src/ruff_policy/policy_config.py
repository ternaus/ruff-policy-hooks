"""Load the Ruff selectors protected by the suppression checker."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

from .selectors import parse_selectors


class PolicyConfigError(ValueError):
    """Raised when protected Ruff selectors are invalid."""


@dataclass(frozen=True)
class Policy:
    """Ruff selectors that must not be suppressed when Ruff enables them."""

    rules: tuple[str, ...]


def policy_from_selectors(values: Iterable[str]) -> Policy:
    """Build a policy from repeated or comma-separated CLI selectors."""
    values = tuple(values)
    if not all(isinstance(item, str) for item in values):
        raise PolicyConfigError("protected selectors must be strings")
    try:
        rules = parse_selectors(values)
    except ValueError as error:
        raise PolicyConfigError(str(error)) from error
    if not rules:
        raise PolicyConfigError("--forbid requires at least one selector")
    return Policy(rules=rules)
