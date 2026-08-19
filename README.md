# ruff-policy-hooks

`ruff-policy-hooks` is a pre-commit hook that prevents accidental suppression
of Ruff diagnostics. It checks Python `noqa` comments and Ruff TOML
configuration. It does not run Ruff, edit files, or calculate code complexity.

## Install with pre-commit

Add the hook to `.pre-commit-config.yaml` and pin a release tag:

```yaml
repos:
  - repo: https://github.com/ternaus/ruff-policy-hooks
    rev: v0.1.0
    hooks:
      - id: check-ruff-suppressions
        args: [--forbid=C901,PLR0912]
        files: ^(src/|tools/|pyproject\.toml$)
```

The hook receives the files selected by pre-commit. Use
`pre-commit run --all-files` in CI when the policy must be audited across the
whole repository.

## Choose a policy

Use `--forbid` when a repository has a small set of mandatory Ruff rules:

```yaml
args:
  - --forbid=C901,PLR0912
  - --max-complexity=10
  - --max-branches=12
```

The hook rejects exact and broader selectors that overlap a forbidden rule.
For example, forbidding `C901` also rejects `C9` and `ALL` in a suppression.

Use `--deny-all` when every suppression must be explicitly allowlisted:

```yaml
args: [--deny-all, --allow=F401,E501]
```

Blanket `# noqa` comments are rejected in both modes. The hook requires a
specific selector even when a path exception is configured.

## Scoped exceptions

For path-specific exceptions, keep the policy in a committed file such as
`.ruff-policy.toml`:

```toml
mode = "forbid"
rules = ["C901", "PLR0912"]
max_complexity = 10
max_branches = 12
require_selected = true

[[path_rules]]
pattern = "tests/*"
allow = ["C901", "PLR0912"]
```

Reference it from the hook:

```yaml
args: [--policy-file=.ruff-policy.toml]
```

Do not combine `--policy-file` with inline policy options. A path rule can
allow a specific suppression in a matching file or Ruff `per-file-ignores`
target. It cannot allow a global Ruff ignore. Use pre-commit `files` and
`exclude` when an entire path should be outside the policy.

## Supported Ruff configuration

The hook reads `pyproject.toml`, `ruff.toml`, and `.ruff.toml`. It checks both
the older `[tool.ruff]` layout and the newer `[tool.ruff.lint]` layout,
including:

- `ignore` and `extend-ignore`;
- `per-file-ignores` and `extend-per-file-ignores`;
- optional `max-complexity` and `max-branches` limits;
- optional selection checks with `require_selected = true`.

The hook uses `tokenize` and TOML parsing from the Python standard library or
the `tomli` compatibility package on Python 3.10. It has no dependency on Ruff
or on the project being checked.

## Local development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest
ruff check .
ruff format --check .
pre-commit run --all-files
```

The repository is released from immutable Git tags. The hook does not need a
PyPI publication: pre-commit installs it directly from GitHub.
