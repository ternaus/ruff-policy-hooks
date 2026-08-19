from pathlib import Path

from ruff_policy.python_comments import Suppression, iter_suppressions


def test_iter_suppressions_reads_inline_file_level_and_blanket_forms(tmp_path: Path) -> None:
    source = tmp_path / "example.py"
    source.write_text(
        "# noqa: c901, PLR0912 - temporary\nvalue = 1  # ruff: noqa: F401\n# noqa\ntext = '# noqa: C901'\n",
        encoding="utf-8",
    )

    assert iter_suppressions(source) == [
        Suppression(1, ("C901", "PLR0912")),
        Suppression(2, ("F401",)),
        Suppression(3, None),
    ]
