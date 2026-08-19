"""Reject suppressions for protected Ruff rules in active code paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .policy_config import Policy
from .python_comments import Suppression, iter_suppressions
from .selectors import selector_covers, selectors_intersect
from .toml_config import DEFAULT_SELECT, RuffConfig, RuffConfigError, find_ruff_config, load_ruff_config


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
    """Check Python files against protected Ruff selectors."""

    def __init__(self, policy: Policy, *, repository_root: Path | None = None) -> None:
        self.policy = policy
        self.repository_root = (repository_root or Path.cwd()).resolve()
        self._config_cache: dict[Path, RuffConfig | RuffConfigError] = {}

    def check_files(self, filenames: tuple[str, ...]) -> list[Violation]:
        """Return violations for the supplied pre-commit filenames."""
        violations: list[Violation] = []
        for filename in filenames:
            path = Path(filename)
            if not path.exists():
                continue
            if path.suffix == ".py":
                violations.extend(self._check_python(path))
        return sorted(violations, key=lambda item: (item.path, item.line or 0, item.message))

    def _display_path(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.repository_root).as_posix()
        except ValueError:
            return str(path)

    def _check_python(self, path: Path) -> list[Violation]:
        display_path = self._display_path(path)
        try:
            config = self._ruff_config_for(path)
        except RuffConfigError as error:
            return [Violation(display_path, None, str(error).split(": ", 1)[-1])]

        relative_path = display_path
        active_rules = self._active_rules(config, relative_path)
        violations: list[Violation] = []
        for suppression in iter_suppressions(path):
            violations.extend(self._check_suppression(display_path, suppression, active_rules))
        return violations

    def _check_suppression(
        self, display_path: str, suppression: Suppression, active_rules: tuple[str, ...]
    ) -> list[Violation]:
        if not active_rules:
            return []
        if suppression.selectors is None:
            return [
                Violation(
                    display_path,
                    suppression.line,
                    "blanket Ruff suppression disables protected selector(s): " + ", ".join(active_rules),
                )
            ]

        forbidden = tuple(
            selector
            for selector in suppression.selectors
            if any(selectors_intersect(selector, rule) for rule in active_rules)
        )
        if forbidden:
            return [
                Violation(
                    display_path,
                    suppression.line,
                    f"Ruff suppression disables protected selector(s): {', '.join(forbidden)}",
                )
            ]
        return []

    def _ruff_config_for(self, path: Path) -> RuffConfig | None:
        config_path = find_ruff_config(path, self.repository_root)
        if config_path is None:
            return None
        cached = self._config_cache.get(config_path)
        if cached is not None:
            if isinstance(cached, RuffConfigError):
                raise cached
            return cached
        try:
            config = load_ruff_config(config_path)
        except RuffConfigError as error:
            self._config_cache[config_path] = error
            raise error
        self._config_cache[config_path] = config
        return config

    def _active_rules(self, config: RuffConfig | None, relative_path: str) -> tuple[str, ...]:
        if config is None:
            selected = DEFAULT_SELECT
            return tuple(
                rule for rule in self.policy.rules if any(selector_covers(selector, rule) for selector in selected)
            )
        return tuple(rule for rule in self.policy.rules if config.is_enabled(rule, relative_path))
