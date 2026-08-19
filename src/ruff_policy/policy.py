"""Apply a Ruff suppression policy to source and TOML files."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from .policy_config import PathRule, Policy
from .python_comments import Suppression, iter_suppressions
from .selectors import (
    selector_covers,
    suppression_hits_forbidden,
    suppression_is_allowed,
)
from .toml_config import RuffConfigError, load_ruff_config

_RUFF_CONFIG_NAMES = {"pyproject.toml", "ruff.toml", ".ruff.toml"}
_DEFAULT_SELECT = ("E4", "E7", "E9", "F")


@dataclass(frozen=True)
class Violation:
    """A policy violation with a preformatted location."""

    path: str
    line: int | None
    message: str

    def format(self) -> str:
        location = f"{self.path}:{self.line}" if self.line is not None else self.path
        return f"{location}: {self.message}"


class PolicyChecker:
    """Check files against a resolved policy."""

    def __init__(self, policy: Policy, *, repository_root: Path | None = None) -> None:
        self.policy = policy
        self.repository_root = (repository_root or Path.cwd()).resolve()

    def check_files(self, filenames: tuple[str, ...]) -> list[Violation]:
        """Return violations for the supplied pre-commit filenames."""
        violations: list[Violation] = []
        for filename in filenames:
            path = Path(filename)
            if not path.exists():
                continue
            if path.suffix == ".py":
                violations.extend(self._check_python(path))
            elif path.name in _RUFF_CONFIG_NAMES:
                violations.extend(self._check_ruff_toml(path))
        return sorted(violations, key=lambda item: (item.path, item.line or 0, item.message))

    def _display_path(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.repository_root).as_posix()
        except ValueError:
            return str(path)

    def _path_rules_for(self, path: str) -> tuple[PathRule, ...]:
        return tuple(rule for rule in self.policy.path_rules if fnmatch.fnmatchcase(path, rule.pattern))

    def _path_rules_for_target(self, target: str) -> tuple[PathRule, ...]:
        normalized = target.replace("\\", "/")
        return tuple(
            rule
            for rule in self.policy.path_rules
            if fnmatch.fnmatchcase(normalized, rule.pattern) or fnmatch.fnmatchcase(rule.pattern, normalized)
        )

    @staticmethod
    def _allowed_selectors(path_rules: tuple[PathRule, ...]) -> tuple[str, ...]:
        return tuple(selector for rule in path_rules for selector in rule.allow)

    def _check_python(self, path: Path) -> list[Violation]:
        display_path = self._display_path(path)
        path_rules = self._path_rules_for(display_path)
        violations: list[Violation] = []
        for suppression in iter_suppressions(path):
            violations.extend(self._check_suppression(display_path, suppression, path_rules))
        return violations

    def _check_suppression(
        self, display_path: str, suppression: Suppression, path_rules: tuple[PathRule, ...]
    ) -> list[Violation]:
        if suppression.selectors is None:
            return [
                Violation(
                    display_path,
                    suppression.line,
                    "blanket Ruff suppression is not allowed; name the specific rule selectors",
                )
            ]

        allowed = self.policy.allow + self._allowed_selectors(path_rules)
        forbidden = tuple(
            selector
            for selector in suppression.selectors
            if self.policy.mode == "forbid"
            and suppression_hits_forbidden(selector, self.policy.rules)
            and not suppression_is_allowed(selector, self._allowed_selectors(path_rules))
        )
        disallowed = tuple(
            selector
            for selector in suppression.selectors
            if self.policy.mode == "deny-all" and not suppression_is_allowed(selector, allowed)
        )
        if forbidden:
            return [
                Violation(
                    display_path,
                    suppression.line,
                    f"Ruff suppression disables forbidden selector(s): {', '.join(forbidden)}",
                )
            ]
        if disallowed:
            return [
                Violation(
                    display_path,
                    suppression.line,
                    f"Ruff suppression is not allowed for selector(s): {', '.join(disallowed)}",
                )
            ]
        return []

    def _check_ruff_toml(self, path: Path) -> list[Violation]:
        try:
            config = load_ruff_config(path)
        except RuffConfigError as error:
            return [Violation(self._display_path(path), None, str(error).split(": ", 1)[-1])]

        violations: list[Violation] = []
        for selectors in config.global_ignores:
            violations.extend(self._check_config_selectors(path, selectors, "global Ruff ignore", ()))
        for target, selectors in config.per_file_ignores:
            path_rules = self._path_rules_for_target(target)
            violations.extend(
                self._check_config_selectors(path, selectors, f"Ruff per-file ignore for {target!r}", path_rules)
            )
        violations.extend(self._check_limits(path, config.max_complexity, config.max_branches))
        if self.policy.require_selected:
            violations.extend(self._check_selected(path, config))
        return violations

    def _check_config_selectors(
        self, path: Path, selectors: tuple[str, ...], context: str, path_rules: tuple[PathRule, ...]
    ) -> list[Violation]:
        allowed = self.policy.allow + self._allowed_selectors(path_rules)
        forbidden = tuple(
            selector
            for selector in selectors
            if self.policy.mode == "forbid"
            and suppression_hits_forbidden(selector, self.policy.rules)
            and not suppression_is_allowed(selector, self._allowed_selectors(path_rules))
        )
        disallowed = tuple(
            selector
            for selector in selectors
            if self.policy.mode == "deny-all" and not suppression_is_allowed(selector, allowed)
        )
        display_path = self._display_path(path)
        if forbidden:
            return [
                Violation(
                    display_path,
                    None,
                    f"{context} disables forbidden selector(s): {', '.join(forbidden)}",
                )
            ]
        if disallowed:
            return [
                Violation(
                    display_path,
                    None,
                    f"{context} is not allowed for selector(s): {', '.join(disallowed)}",
                )
            ]
        return []

    def _check_limits(self, path: Path, max_complexity: int | None, max_branches: int | None) -> list[Violation]:
        display_path = self._display_path(path)
        violations: list[Violation] = []
        if (
            self.policy.max_complexity is not None
            and max_complexity is not None
            and max_complexity > self.policy.max_complexity
        ):
            violations.append(
                Violation(
                    display_path,
                    None,
                    f"max-complexity must not exceed {self.policy.max_complexity}",
                )
            )
        if (
            self.policy.max_branches is not None
            and max_branches is not None
            and max_branches > self.policy.max_branches
        ):
            violations.append(
                Violation(
                    display_path,
                    None,
                    f"max-branches must not exceed {self.policy.max_branches}",
                )
            )
        return violations

    def _check_selected(self, path: Path, config) -> list[Violation]:
        if self.policy.mode != "forbid":
            return []
        selected = config.select if config.select is not None else _DEFAULT_SELECT
        selected = selected + config.extend_select
        missing = tuple(
            rule for rule in self.policy.rules if not any(selector_covers(selector, rule) for selector in selected)
        )
        if not missing:
            return []
        return [
            Violation(
                self._display_path(path),
                None,
                f"required Ruff selector(s) are not selected: {', '.join(missing)}",
            )
        ]
