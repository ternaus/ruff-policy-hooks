from pathlib import Path

from ruff_policy.toml_config import load_ruff_config

EXPECTED_MAX_COMPLEXITY = 10
EXPECTED_MAX_BRANCHES = 12


def test_load_pyproject_old_and_new_ruff_layouts(tmp_path: Path) -> None:
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text(
        "[tool.ruff]\n"
        "select = ['ALL']\n"
        "ignore = ['F401']\n"
        "extend-ignore = ['E501']\n"
        "[tool.ruff.lint]\n"
        "extend-select = ['C901']\n"
        "per-file-ignores = { 'tests/*' = ['PLR0912'] }\n"
        "extend-per-file-ignores = { 'tools/*' = ['F401'] }\n"
        "[tool.ruff.lint.mccabe]\n"
        "max-complexity = 10\n"
        "[tool.ruff.lint.pylint]\n"
        "max-branches = 12\n",
        encoding="utf-8",
    )

    config = load_ruff_config(config_path)

    assert config.select == ("ALL",)
    assert config.extend_select == ("C901",)
    assert config.global_ignores == (("F401",), ("E501",))
    assert config.per_file_ignores == (("tests/*", ("PLR0912",)), ("tools/*", ("F401",)))
    assert config.max_complexity == EXPECTED_MAX_COMPLEXITY
    assert config.max_branches == EXPECTED_MAX_BRANCHES


def test_load_standalone_ruff_toml(tmp_path: Path) -> None:
    config_path = tmp_path / ".ruff.toml"
    config_path.write_text("[lint]\nignore = ['C901']\n", encoding="utf-8")

    assert load_ruff_config(config_path).global_ignores == (("C901",),)
