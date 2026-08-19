from pathlib import Path

from ruff_policy.cli import main

EXPECTED_ARGUMENT_ERROR = 2


def test_cli_returns_failure_and_prints_violation(tmp_path: Path, capsys) -> None:
    source = tmp_path / "example.py"
    source.write_text("value = 1  # noqa: C901\n", encoding="utf-8")

    result = main(["check", "--forbid=C901", str(source)])

    assert result == 1
    assert f"{source}:1: Ruff suppression disables forbidden selector(s): C901" in capsys.readouterr().out


def test_cli_requires_a_policy(capsys) -> None:
    try:
        main(["check"])
    except SystemExit as error:
        assert error.code == EXPECTED_ARGUMENT_ERROR
    else:
        raise AssertionError("CLI accepted a missing policy")
    assert "choose --forbid, --deny-all, or --policy-file" in capsys.readouterr().err
