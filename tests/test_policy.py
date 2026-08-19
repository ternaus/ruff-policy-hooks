from pathlib import Path

from ruff_policy.policy import PolicyChecker
from ruff_policy.policy_config import Policy

EXPECTED_VIOLATIONS = 4


def check(tmp_path: Path, policy: Policy, *filenames: str) -> list[str]:
    return [
        violation.format()
        for violation in PolicyChecker(policy, repository_root=tmp_path).check_files(
            tuple(str(tmp_path / filename) for filename in filenames)
        )
    ]


def write_ruff_config(tmp_path: Path, content: str) -> None:
    (tmp_path / "pyproject.toml").write_text(content, encoding="utf-8")


def test_forbid_mode_rejects_exact_family_and_all_suppressions(tmp_path: Path) -> None:
    write_ruff_config(tmp_path, "[tool.ruff.lint]\nselect = ['C90']\n")
    source = tmp_path / "example.py"
    source.write_text(
        "def first():  # noqa: C901\n    return 1\n"
        "def second():  # noqa: C9\n    return 2\n"
        "def third():  # noqa: ALL\n    return 3\n"
        "# noqa\nvalue = 4\n",
        encoding="utf-8",
    )

    violations = check(tmp_path, Policy(rules=("C901",)), "example.py")

    assert len(violations) == EXPECTED_VIOLATIONS
    assert violations[0].startswith("example.py:1: Ruff suppression disables protected selector(s): C901")
    assert violations[1].startswith("example.py:3: Ruff suppression disables protected selector(s): C9")
    assert violations[2].startswith("example.py:5: Ruff suppression disables protected selector(s): ALL")
    assert "blanket Ruff suppression disables protected selector(s): C901" in violations[3]


def test_only_active_rules_are_protected_for_each_path(tmp_path: Path) -> None:
    write_ruff_config(
        tmp_path,
        "[tool.ruff.lint]\nselect = ['C90', 'PLR']\nper-file-ignores = { 'tests/*' = ['C90', 'PLR'] }\n",
    )
    source = tmp_path / "example.py"
    source.write_text("value = 1  # noqa: F401\nvalue = 2  # noqa: C901\n", encoding="utf-8")
    test_source = tmp_path / "tests" / "example.py"
    test_source.parent.mkdir()
    test_source.write_text("value = 1  # noqa: C901\n# noqa\n", encoding="utf-8")
    policy = Policy(rules=("C901", "PLR0912"))

    assert check(tmp_path, policy, "example.py") == [
        "example.py:2: Ruff suppression disables protected selector(s): C901"
    ]
    assert check(tmp_path, policy, "tests/example.py") == []


def test_inactive_rules_allow_suppressions(tmp_path: Path) -> None:
    write_ruff_config(tmp_path, "[tool.ruff.lint]\nselect = ['F']\n")
    source = tmp_path / "example.py"
    source.write_text(
        "value = 1  # noqa: C901\n# noqa\n",
        encoding="utf-8",
    )

    assert check(tmp_path, Policy(rules=("C901",)), "example.py") == []


def test_global_ignore_disables_enforcement(tmp_path: Path) -> None:
    write_ruff_config(tmp_path, "[tool.ruff.lint]\nselect = ['C90']\nignore = ['C901']\n")
    source = tmp_path / "example.py"
    source.write_text("value = 1  # noqa: C901\n", encoding="utf-8")

    assert check(tmp_path, Policy(rules=("C901",)), "example.py") == []


def test_malformed_toml_is_reported(tmp_path: Path) -> None:
    config = tmp_path / ".ruff.toml"
    config.write_text("[lint\n", encoding="utf-8")

    source = tmp_path / "example.py"
    source.write_text("value = 1  # noqa: C901\n", encoding="utf-8")

    violations = check(tmp_path, Policy(rules=("C901",)), "example.py")

    assert len(violations) == 1
    assert violations[0].startswith("example.py: cannot parse TOML:")
