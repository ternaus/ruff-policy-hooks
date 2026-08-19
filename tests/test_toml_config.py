from pathlib import Path

from ruff_policy.toml_config import find_ruff_config, load_ruff_config


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
        "extend-per-file-ignores = { 'tools/*' = ['F401'] }\n",
        encoding="utf-8",
    )

    config = load_ruff_config(config_path)

    assert config.select == ("ALL",)
    assert config.extend_select == ("C901",)
    assert config.global_ignores == (("F401",), ("E501",))
    assert config.per_file_ignores == (("tests/*", ("PLR0912",)), ("tools/*", ("F401",)))
    assert config.is_enabled("C901", "src/app.py")
    assert not config.is_enabled("PLR0912", "tests/app.py")
    assert not config.is_enabled("F401", "tools/app.py")


def test_load_standalone_ruff_toml(tmp_path: Path) -> None:
    config_path = tmp_path / ".ruff.toml"
    config_path.write_text("[lint]\nignore = ['C901']\n", encoding="utf-8")

    config = load_ruff_config(config_path)

    assert config.global_ignores == (("C901",),)
    assert not config.is_enabled("C901", "src/app.py")


def test_find_ruff_config_walks_to_repository_root(tmp_path: Path) -> None:
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text("[tool.ruff.lint]\nselect = ['C90']\n", encoding="utf-8")
    source = tmp_path / "src" / "app.py"
    source.parent.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")

    assert find_ruff_config(source, tmp_path) == config_path
