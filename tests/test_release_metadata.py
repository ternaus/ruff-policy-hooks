import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib


ROOT = Path(__file__).parents[1]
HOOK_REPOSITORY = "https://github.com/ternaus/ruff-policy-hooks"


def test_readme_hook_revision_matches_project_version() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    pattern = rf"repo:\s+{re.escape(HOOK_REPOSITORY)}\s+rev:\s+v(?P<version>[^\s#]+)"

    matches = re.findall(pattern, readme)

    assert matches == [version], "README hook revision must match pyproject.toml project.version"
