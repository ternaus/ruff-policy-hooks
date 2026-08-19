# ruff-policy-hooks

This pre-commit hook protects selected Ruff rules from being disabled in
source code with `noqa` comments.

You list the protected Ruff selectors in the hook. The hook reads the
repository's Ruff configuration to decide whether each selector is active for
the file being checked, and fails if a protected selector is disabled in the
repository-wide configuration.

The hook does not change Ruff configuration. It does not run Ruff or calculate
complexity.

## Goal

Ruff configuration decides which rules apply to each Python file. When a
protected rule is enabled for a file, it must remain enabled throughout that
file.

The `--protect` list must agree with the repository-wide Ruff configuration. If
Ruff does not select a protected rule, or globally ignores it, the hook fails
with a configuration error. This catches a rule that was protected in the hook
but quietly disabled in `pyproject.toml`.

A developer or AI coding agent may try to make the rule disappear for one
function or line by adding `# noqa`. The hook rejects that code change. The
code must be refactored. Path-specific `per-file-ignores` remain Ruff's source
of truth for exceptions such as test files.

This is an automated guardrail for code changes made by both developers and AI
agents. It prevents a local suppression from quietly bypassing a rule or
passing unnoticed in code review.

## Example: protect C901

Suppose Ruff enables `C901` for `src/`, and the hook protects that rule:

```yaml
args: [--protect=C901]
```

This code in `src/` fails the pre-commit hook:

```python
def build_result():  # noqa: C901
    ...
```

The expected fix is to refactor `build_result`. Broader selectors such as `C9`
and `ALL`, and blanket `# noqa` comments, fail for the same reason: they can
hide `C901`.

This configuration error also fails, even if the source code contains no
`noqa` comments:

```toml
[tool.ruff.lint]
select = ["ALL"]
ignore = ["C901"]
```

The fix is to remove `C901` from Ruff's global ignores or remove `C901` from the
hook's `--protect` list.

Suppressions for unrelated rules remain allowed. For example, this is allowed
when `F401` is not protected:

```python
import optional_module  # noqa: F401
```

If Ruff disables `C901` for `tests/`, the hook does not enforce it there:

```toml
[tool.ruff.lint]
select = ["C901"]
per-file-ignores = { "tests/*" = ["C901"] }
```

The same `# noqa: C901` is therefore allowed in `tests/` and blocked in `src/`.
The hook follows the nearest Ruff configuration for each Python file, including
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
selectors, requires them to be enabled globally, and follows Ruff for
path-specific exceptions.

The hook receives Python and Ruff configuration files selected by pre-commit.
Use `pre-commit run --all-files` in CI when every Python file and Ruff
configuration file must be checked.

## When a commit is blocked

If a protected selector is not enabled by Ruff globally, either enable it in
Ruff or remove it from `--protect`. If a source suppression is blocked, remove
the suppression and simplify or split the code. If the rule is not relevant for
a path, configure that exception in Ruff's normal `per-file-ignores`; the hook
will follow it.

The hook does not block suppressions for rules outside its protected list. It
also does not enforce numeric settings such as `max-complexity` or
`max-branches`.

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
