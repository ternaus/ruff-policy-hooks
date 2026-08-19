# ruff-policy-hooks

This pre-commit hook stops `noqa` comments from hiding the Ruff rules that your
repository uses to control code complexity.

You list the protected Ruff selectors in the hook. The hook reads the
repository's Ruff configuration to decide whether each selector is active for
the file being checked. Ruff remains the source of truth for that scope.

The hook does not validate or change Ruff configuration. It does not run Ruff
or calculate complexity.

## What it blocks

Suppose the hook protects `C901` and Ruff enables that rule for `src/`:

```python
def build_result():  # noqa: C901  # blocked
    ...
```

When a protected rule is active, the hook also blocks broader selectors such as
`C9` and `ALL`, and blanket `# noqa` comments, because they hide the protected
rule.

Suppressions for other rules remain allowed:

```python
import optional_module  # noqa: F401  # allowed when F401 is not protected
```

If Ruff disables `C901` for a path, the hook follows Ruff and allows the
suppression there:

```toml
[tool.ruff.lint]
select = ["C90"]
per-file-ignores = { "tests/*" = ["C901"] }
```

The same `# noqa: C901` can therefore be allowed in `tests/` and blocked in
`src/`. The hook checks the Ruff configuration that is nearest to each Python
file, including `select`, `extend-select`, `ignore`, `extend-ignore`,
`per-file-ignores`, and `extend-per-file-ignores`.

## Install with pre-commit

Add the hook and pin a release tag:

```yaml
repos:
  - repo: https://github.com/ternaus/ruff-policy-hooks
    rev: v0.2.0
    hooks:
      - id: check-ruff-suppressions
        args: [--forbid=C901,PLR0912]
```

The list is intentionally kept in the hook because Ruff does not mark which
selected rules are important to your repository. The hook protects only those
selectors, and only where Ruff has them enabled.

The hook receives Python files selected by pre-commit. Use
`pre-commit run --all-files` in CI when every Python file must be checked.

## When a commit is blocked

Remove the suppression and simplify or split the code. If the rule is not
relevant for a path, configure that exception in Ruff's normal
`per-file-ignores`; the hook will follow it.

The hook does not block suppressions for rules outside its protected list. It
also does not block changes to `max-complexity`, `max-branches`, or other Ruff
settings.

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

Pre-commit installs the hook directly from GitHub. The repository being checked
does not need a dependency on Ruff for this hook.
