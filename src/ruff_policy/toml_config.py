"""Extract the Ruff settings relevant to suppression policy."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib

from .selectors import parse_selectors


class RuffConfigError(ValueError):
    """Raised when a Ruff configuration has an unsupported shape."""


@dataclass(frozen=True)
class RuffConfig:
    """Ruff settings needed by the policy checker."""

    path: Path
    global_ignores: tuple[tuple[str, ...], ...]
    per_file_ignores: tuple[tuple[str, tuple[str, ...]], ...]
    select: tuple[str, ...] | None
    extend_select: tuple[str, ...]
    max_complexity: int | None
    max_branches: int | None


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


def _nested_int(section: Mapping[str, Any], group: str, key: str) -> int | None:
    value = _mapping(section.get(group)).get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Ruff setting {group}.{key!s} must be an integer")
    return value


def _get_nested_int(base: Mapping[str, Any], lint: Mapping[str, Any], group: str, key: str) -> int | None:
    for section in (lint, base):
        value = _nested_int(section, group, key)
        if value is not None:
            return value
    return None


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

    try:
        max_complexity = _get_nested_int(root, lint, "mccabe", "max-complexity")
        max_branches = _get_nested_int(root, lint, "pylint", "max-branches")
    except ValueError as error:
        raise RuffConfigError(f"{path}: {error}") from error

    return RuffConfig(
        path=path,
        global_ignores=global_ignores,
        per_file_ignores=per_file_ignores,
        select=select,
        extend_select=extend_select,
        max_complexity=max_complexity,
        max_branches=max_branches,
    )
