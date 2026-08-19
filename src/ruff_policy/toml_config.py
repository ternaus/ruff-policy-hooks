"""Read the Ruff settings needed to resolve active rules for each file."""

from __future__ import annotations

import fnmatch
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib

from .selectors import parse_selectors, selector_covers, selectors_intersect

_RUFF_CONFIG_NAMES = ("ruff.toml", ".ruff.toml", "pyproject.toml")
DEFAULT_SELECT = ("E4", "E7", "E9", "F")


class RuffConfigError(ValueError):
    """Raised when a Ruff configuration has an unsupported shape."""


@dataclass(frozen=True)
class RuffConfig:
    """Ruff settings needed to determine whether a rule is active for a file."""

    path: Path
    global_ignores: tuple[tuple[str, ...], ...]
    per_file_ignores: tuple[tuple[str, tuple[str, ...]], ...]
    select: tuple[str, ...] | None
    extend_select: tuple[str, ...]

    def _flattened_global_ignores(self) -> tuple[str, ...]:
        """Return global ignore selectors as one tuple."""
        return tuple(selector for selectors in self.global_ignores for selector in selectors)

    def is_globally_enabled(self, rule: str) -> bool:
        """Return whether Ruff enables *rule* in the repository configuration."""
        selected = self.select if self.select is not None else DEFAULT_SELECT
        selected = selected + self.extend_select
        if not any(selector_covers(selector, rule) for selector in selected):
            return False

        ignored = self._flattened_global_ignores()
        return not any(selectors_intersect(rule, selector) for selector in ignored)

    def is_enabled(self, rule: str, relative_path: str) -> bool:
        """Return whether Ruff enables *rule* for *relative_path*."""
        if not self.is_globally_enabled(rule):
            return False

        ignored = self._flattened_global_ignores()
        ignored += tuple(
            selector
            for target, selectors in self.per_file_ignores
            if fnmatch.fnmatchcase(relative_path, target)
            for selector in selectors
        )
        return not any(selectors_intersect(rule, selector) for selector in ignored)


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _selector_list(value: object, *, path: Path, key: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RuffConfigError(f"{path}: Ruff setting {key!r} must be a list of strings")
    try:
        return parse_selectors(value)
    except ValueError as error:
        raise RuffConfigError(f"{path}: {error}") from error


def _collect_selector_lists(
    base: Mapping[str, Any], lint: Mapping[str, Any], *, path: Path, key: str
) -> tuple[tuple[str, ...], ...]:
    return tuple(
        selectors for section in (base, lint) if (selectors := _selector_list(section.get(key), path=path, key=key))
    )


def _collect_per_file_ignores(
    base: Mapping[str, Any], lint: Mapping[str, Any], *, path: Path, key: str
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    entries: list[tuple[str, tuple[str, ...]]] = []
    for section in (base, lint):
        value = section.get(key)
        if value is None:
            continue
        if not isinstance(value, Mapping):
            raise RuffConfigError(f"{path}: Ruff setting {key!r} must be a table")
        for target, rules in value.items():
            if not isinstance(target, str):
                raise RuffConfigError(f"{path}: Ruff {key!r} targets must be strings")
            selectors = _selector_list(rules, path=path, key=f"{key}.{target}")
            if selectors:
                entries.append((target, selectors))
    return tuple(entries)


def load_ruff_config(path: Path) -> RuffConfig:
    """Load a supported Ruff TOML file."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise RuffConfigError(f"{path}: cannot parse TOML: {error}") from error

    if path.name == "pyproject.toml":
        tool = _mapping(data.get("tool"))
        root = _mapping(tool.get("ruff"))
    else:
        root = _mapping(data)
    lint = _mapping(root.get("lint"))

    select_value = lint.get("select", root.get("select"))
    select = _selector_list(select_value, path=path, key="select") if select_value is not None else None
    extend_select = tuple(
        selector
        for values in _collect_selector_lists(root, lint, path=path, key="extend-select")
        for selector in values
    )
    global_ignores = tuple(
        selectors
        for key in ("ignore", "extend-ignore")
        for selectors in _collect_selector_lists(root, lint, path=path, key=key)
    )
    per_file_ignores = tuple(
        entry
        for key in ("per-file-ignores", "extend-per-file-ignores")
        for entry in _collect_per_file_ignores(root, lint, path=path, key=key)
    )

    return RuffConfig(
        path=path,
        global_ignores=global_ignores,
        per_file_ignores=per_file_ignores,
        select=select,
        extend_select=extend_select,
    )


def find_ruff_config(path: Path, repository_root: Path) -> Path | None:
    """Find the nearest Ruff configuration between *path* and the repository root."""
    root = repository_root.resolve()
    directory = path.resolve().parent
    while True:
        for name in _RUFF_CONFIG_NAMES:
            candidate = directory / name
            if candidate.is_file():
                return candidate
        if directory == root or root not in directory.parents:
            return None
        directory = directory.parent
