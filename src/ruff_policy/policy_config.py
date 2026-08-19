"""Load policy settings for the Ruff suppression checker."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib

from .selectors import parse_selectors

PolicyMode = Literal["forbid", "deny-all"]


class PolicyConfigError(ValueError):
    """Raised when policy arguments or a policy file are invalid."""


@dataclass(frozen=True)
class PathRule:
    """Allow additional selectors for a repository-relative path pattern."""

    pattern: str
    allow: tuple[str, ...]


@dataclass(frozen=True)
class Policy:
    """Resolved suppression policy."""

    mode: PolicyMode
    rules: tuple[str, ...] = ()
    allow: tuple[str, ...] = ()
    max_complexity: int | None = None
    max_branches: int | None = None
    require_selected: bool = False
    path_rules: tuple[PathRule, ...] = ()


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list_of_strings(value: object, *, label: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PolicyConfigError(f"{label} must be a list of strings")
    try:
        return parse_selectors(value)
    except ValueError as error:
        raise PolicyConfigError(str(error)) from error


def _optional_int(value: object, *, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise PolicyConfigError(f"{label} must be an integer")
    return value


def _normalize_pattern(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PolicyConfigError(f"{label} must be a non-empty path pattern")
    pattern = value.strip().replace("\\", "/")
    return pattern[2:] if pattern.startswith("./") else pattern


def _path_rules(value: object) -> tuple[PathRule, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise PolicyConfigError("path_rules must be an array of tables")
    rules: list[PathRule] = []
    for index, item in enumerate(value):
        table = _mapping(item)
        pattern = _normalize_pattern(table.get("pattern"), label=f"path_rules[{index}].pattern")
        allow = _list_of_strings(table.get("allow"), label=f"path_rules[{index}].allow")
        if "ALL" in allow:
            raise PolicyConfigError("path rules cannot allow the ALL selector")
        rules.append(PathRule(pattern, allow))
    return tuple(rules)


def _build_policy(data: Mapping[str, Any]) -> Policy:
    mode = data.get("mode")
    if mode not in ("forbid", "deny-all"):
        raise PolicyConfigError("policy mode must be 'forbid' or 'deny-all'")

    rules = _list_of_strings(data.get("rules"), label="rules")
    allow = _list_of_strings(data.get("allow"), label="allow")
    if "ALL" in allow:
        raise PolicyConfigError("allow cannot contain the ALL selector")
    if mode == "forbid" and allow:
        raise PolicyConfigError("allow is only valid in deny-all mode; use path_rules for scoped exceptions")
    if mode == "deny-all" and rules:
        raise PolicyConfigError("rules is only valid in forbid mode")
    require_selected = data.get("require_selected", False)
    if not isinstance(require_selected, bool):
        raise PolicyConfigError("require_selected must be a boolean")
    if mode == "forbid" and not rules:
        raise PolicyConfigError("forbid mode requires at least one rule")
    if mode == "deny-all" and require_selected:
        raise PolicyConfigError("require_selected is only valid in forbid mode")

    return Policy(
        mode=mode,
        rules=rules,
        allow=allow,
        max_complexity=_optional_int(data.get("max_complexity"), label="max_complexity"),
        max_branches=_optional_int(data.get("max_branches"), label="max_branches"),
        require_selected=require_selected,
        path_rules=_path_rules(data.get("path_rules")),
    )


def load_policy_file(path: Path) -> Policy:
    """Load a policy TOML file."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise PolicyConfigError(f"{path}: cannot parse TOML: {error}") from error
    try:
        return _build_policy(_mapping(data))
    except PolicyConfigError as error:
        raise PolicyConfigError(f"{path}: {error}") from error
