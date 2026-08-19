# ruff-policy-hooks

This pre-commit hook stops `noqa` comments from hiding Ruff diagnostics that
your repository wants to keep visible.

You list the protected Ruff selectors in the hook. The hook reads the
repository's Ruff configuration to decide whether each selector is active for
the file being checked. Ruff remains the source of truth for that scope.

The hook does not validate or change Ruff configuration. It does not run Ruff
or calculate complexity.

## Why this hook exists

Ruff warns when code is too complex. A rushed contributor or coding agent can
make that warning disappear by adding `# noqa` instead of refactoring. The
change can look like one harmless comment and be easy to miss in code review.

This hook blocks that shortcut for the rules you protect. A `# noqa` comment is
called a suppression: it tells Ruff to skip a diagnostic.

## Example: protect C901

Suppose you want Ruff's C901 complexity check to remain active in `src/`:

```yaml
args: [--protect=C901]
```

This code now fails the pre-commit hook:

```python
def build_result():  # noqa: C901
    ...
```

The expected fix is a refactor. Broader selectors such as `C9` and `ALL`, and
blanket `# noqa` comments, fail for the same reason.

Suppressions for unrelated rules remain allowed:

```python
import optional_module  # noqa: F401
```

If Ruff disables C901 for tests, the hook leaves that path alone:

```toml
[tool.ruff.lint]
select = ["C90"]
per-file-ignores = { "tests/*" = ["C901"] }
```

The same `# noqa: C901` is allowed in `tests/` and still blocked in `src/`. The
hook follows the nearest Ruff configuration for each Python file, including
`select`, `extend-select`, `ignore`, `extend-ignore`, `per-file-ignores`, and
`extend-per-file-ignores`.

## Install with pre-commit

Add the hook and pin a release tag:

```yaml
repos:
  - repo: https://github.com/ternaus/ruff-policy-hooks
    rev: v0.3.0
    hooks:
      - id: check-ruff-suppressions
        args: [--protect=C901,PLR0912]
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
