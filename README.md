# ruff-policy-hooks

Ruff can find code that is too complex, but a contributor or coding agent can
silence that warning with `# noqa` or a Ruff ignore setting. This pre-commit
hook protects the Ruff rules that your repository considers mandatory.

It blocks a commit when a protected rule is disabled in Python code or in a
Ruff TOML configuration. It does not run Ruff, change files, or calculate code
complexity.

## What the hook forbids

With a policy such as `--forbid=C901,PLR0912`, the hook forbids:

- `# noqa: C901` and `# ruff: noqa: PLR0912` in Python files;
- broader selectors such as `C9` or `ALL`, because they also disable a
  protected rule;
- Ruff `ignore`, `extend-ignore`, and matching `per-file-ignores` settings;
- raising `max-complexity` or `max-branches` beyond the configured limits.

The last item is checked only when the corresponding limit is configured. A
suppression for an unrelated rule remains allowed in `forbid` mode:

```python
unused_import = value  # noqa: F401  — allowed when only C901 is protected
complex_function()  # noqa: C901  — blocked
```

Blanket suppressions are always blocked. The hook requires a rule name, even
when a path exception exists:

```python
value = build_value()  # noqa  — blocked
```

With `--deny-all`, every rule suppression is blocked unless that rule is
explicitly allowlisted. Use this mode when the repository does not want
silenced Ruff diagnostics at all.

The hook checks only files passed to it by pre-commit. Therefore, the
repository's `files` and `exclude` settings decide where the policy applies.
Run `pre-commit run --all-files` in CI when the whole repository must be
audited.

## Install with pre-commit

Add the hook and pin a release tag:

```yaml
repos:
  - repo: https://github.com/ternaus/ruff-policy-hooks
    rev: v0.1.0
    hooks:
      - id: check-ruff-suppressions
        args: [--forbid=C901,PLR0912]
        files: ^(src/|tools/|pyproject\.toml$)
```

## Choose a policy

Use `--forbid` when only a few Ruff rules are mandatory:

```yaml
args:
  - --forbid=C901,PLR0912
  - --max-complexity=10
  - --max-branches=12
```

Use `--deny-all` when every suppression must be explicitly allowed:

```yaml
args: [--deny-all, --allow=F401,E501]
```

For path-specific exceptions, keep the policy in a committed file. This
example permits the protected complexity rules in tests, while keeping them
forbidden everywhere else:

```toml
mode = "forbid"
rules = ["C901", "PLR0912"]

[[path_rules]]
pattern = "tests/*"
allow = ["C901", "PLR0912"]
```

Reference the file from the hook:

```yaml
args: [--policy-file=.ruff-policy.toml]
```

A path rule can allow a specific suppression in a matching file or Ruff
`per-file-ignores` target. It cannot allow a global Ruff ignore. Use pre-commit
`files` or `exclude` when an entire path should be outside the policy.

Do not combine `--policy-file` with inline policy options. Add
`require_selected = true` to a `forbid` policy when protected rules must also
be present in Ruff's `select` configuration.

## When a commit is blocked

First remove the suppression and simplify or split the code. If the exception
is intentional, make it narrow: name the exact rule and, when needed, add a
path-specific allowlist to the policy file. Avoid blanket `# noqa` comments and
`ALL`; they hide more diagnostics than the exception explains.

## Supported Ruff configuration

The hook reads `pyproject.toml`, `ruff.toml`, and `.ruff.toml`, in both the
older `[tool.ruff]` layout and the newer `[tool.ruff.lint]` layout. It checks
`ignore`, `extend-ignore`, `per-file-ignores`, and
`extend-per-file-ignores`, plus the optional complexity limits and selection
requirement described above.

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

Pre-commit installs the hook directly from GitHub; it does not need a PyPI
publication or a dependency on Ruff in the repository being checked.
