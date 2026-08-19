from pathlib import Path

import pytest

from ruff_policy.policy_config import PolicyConfigError, load_policy_file

EXPECTED_MAX_COMPLEXITY = 10


def test_load_policy_file(tmp_path: Path) -> None:
    policy_path = tmp_path / ".ruff-policy.toml"
    policy_path.write_text(
        "mode = 'forbid'\n"
        "rules = ['C901', 'PLR0912']\n"
        "max_complexity = 10\n"
        "require_selected = true\n"
        "[[path_rules]]\n"
        "pattern = 'tests/*'\n"
        "allow = ['C901', 'PLR0912']\n",
        encoding="utf-8",
    )

    policy = load_policy_file(policy_path)

    assert policy.mode == "forbid"
    assert policy.rules == ("C901", "PLR0912")
    assert policy.max_complexity == EXPECTED_MAX_COMPLEXITY
    assert policy.require_selected is True
    assert policy.path_rules[0].pattern == "tests/*"


def test_policy_file_rejects_ambiguous_allowlist(tmp_path: Path) -> None:
    policy_path = tmp_path / ".ruff-policy.toml"
    policy_path.write_text("mode = 'forbid'\nrules = ['C901']\nallow = ['F401']\n", encoding="utf-8")

    with pytest.raises(PolicyConfigError, match="allow is only valid"):
        load_policy_file(policy_path)
