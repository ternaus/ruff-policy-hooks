from pathlib import Path

from ruff_policy.policy import PolicyChecker
from ruff_policy.policy_config import PathRule, Policy

EXPECTED_VIOLATIONS = 4


def check(tmp_path: Path, policy: Policy, *filenames: str) -> list[str]:
    return [
        violation.format()
        for violation in PolicyChecker(policy, repository_root=tmp_path).check_files(
            tuple(str(tmp_path / filename) for filename in filenames)
        )
    ]


def test_forbid_mode_rejects_exact_family_and_all_suppressions(tmp_path: Path) -> None:
    source = tmp_path / "example.py"
    source.write_text(
        "def first():  # noqa: C901\n    return 1\n"
        "def second():  # noqa: C9\n    return 2\n"
        "def third():  # noqa: ALL\n    return 3\n"
        "# noqa\nvalue = 4\n",
        encoding="utf-8",
    )

    violations = check(tmp_path, Policy(mode="forbid", rules=("C901",)), "example.py")

    assert len(violations) == EXPECTED_VIOLATIONS
    assert violations[0].startswith("example.py:1: Ruff suppression disables forbidden selector(s): C901")
    assert violations[1].startswith("example.py:3: Ruff suppression disables forbidden selector(s): C9")
    assert violations[2].startswith("example.py:5: Ruff suppression disables forbidden selector(s): ALL")
    assert "blanket Ruff suppression" in violations[3]


def test_forbid_mode_allows_other_rules_and_scoped_test_exception(tmp_path: Path) -> None:
    source = tmp_path / "example.py"
    source.write_text("value = 1  # noqa: F401\n", encoding="utf-8")
    test_source = tmp_path / "tests" / "example.py"
    test_source.parent.mkdir()
    test_source.write_text("value = 1  # noqa: C901\n", encoding="utf-8")
    policy = Policy(
        mode="forbid",
        rules=("C901",),
        path_rules=(PathRule("tests/*", ("C901",)),),
    )

    assert check(tmp_path, policy, "example.py") == []
    assert check(tmp_path, policy, "tests/example.py") == []


def test_deny_all_requires_specific_allowlist(tmp_path: Path) -> None:
    source = tmp_path / "example.py"
    source.write_text(
        "value = 1  # noqa: F401\nother = 2  # noqa: C901\n",
        encoding="utf-8",
    )

    violations = check(tmp_path, Policy(mode="deny-all", allow=("F401",)), "example.py")

    assert violations == ["example.py:2: Ruff suppression is not allowed for selector(s): C901"]


def test_toml_policy_checks_global_per_file_and_limits(tmp_path: Path) -> None:
    config = tmp_path / "pyproject.toml"
    config.write_text(
        "[tool.ruff.lint]\n"
        "ignore = ['C901']\n"
        "per-file-ignores = { 'src/*' = ['PLR0912'], 'tests/*' = ['C901'] }\n"
        "[tool.ruff.lint.mccabe]\n"
        "max-complexity = 11\n"
        "[tool.ruff.lint.pylint]\n"
        "max-branches = 13\n",
        encoding="utf-8",
    )
    policy = Policy(
        mode="forbid",
        rules=("C901", "PLR0912"),
        max_complexity=10,
        max_branches=12,
        path_rules=(PathRule("tests/*", ("C901", "PLR0912")),),
    )

    violations = check(tmp_path, policy, "pyproject.toml")

    assert len(violations) == EXPECTED_VIOLATIONS
    assert any("global Ruff ignore" in violation for violation in violations)
    assert any("src/*" in violation for violation in violations)
    assert any("max-complexity" in violation for violation in violations)
    assert any("max-branches" in violation for violation in violations)


def test_deny_all_checks_toml_ignores_and_path_allowlist(tmp_path: Path) -> None:
    config = tmp_path / "ruff.toml"
    config.write_text(
        "[lint]\nignore = ['F401']\n[lint.per-file-ignores]\n'tests/*' = ['E501']\n",
        encoding="utf-8",
    )
    policy = Policy(
        mode="deny-all",
        allow=("E501",),
        path_rules=(PathRule("tests/*", ("E501",)),),
    )

    violations = check(tmp_path, policy, "ruff.toml")

    assert violations == ["ruff.toml: global Ruff ignore is not allowed for selector(s): F401"]


def test_require_selected_rejects_missing_forbidden_rules(tmp_path: Path) -> None:
    config = tmp_path / "pyproject.toml"
    config.write_text("[tool.ruff.lint]\nselect = ['E4', 'F']\n", encoding="utf-8")
    policy = Policy(mode="forbid", rules=("C901",), require_selected=True)

    assert check(tmp_path, policy, "pyproject.toml") == [
        "pyproject.toml: required Ruff selector(s) are not selected: C901"
    ]


def test_malformed_toml_is_reported(tmp_path: Path) -> None:
    config = tmp_path / ".ruff.toml"
    config.write_text("[lint\n", encoding="utf-8")

    violations = check(tmp_path, Policy(mode="forbid", rules=("C901",)), ".ruff.toml")

    assert len(violations) == 1
    assert violations[0].startswith(".ruff.toml: cannot parse TOML:")
