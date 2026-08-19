"""Command-line interface for the Ruff policy hook."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .policy import PolicyChecker
from .policy_config import Policy, PolicyConfigError, load_policy_file
from .selectors import parse_selectors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ruff-policy")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check Python and Ruff TOML files")
    mode = check.add_mutually_exclusive_group()
    mode.add_argument("--forbid", action="append", default=[], help="Ruff selectors that must not be suppressed")
    mode.add_argument("--deny-all", action="store_true", help="reject every suppression except --allow selectors")
    check.add_argument("--allow", action="append", default=[], help="selectors allowed with --deny-all")
    check.add_argument("--policy-file", type=Path, help="read policy from a TOML file")
    check.add_argument("--max-complexity", type=int, help="maximum permitted Ruff mccabe limit")
    check.add_argument("--max-branches", type=int, help="maximum permitted Ruff pylint branch limit")
    check.add_argument(
        "--require-selected", action="store_true", help="require forbidden selectors to be selected by Ruff"
    )
    check.add_argument("filenames", nargs="*", help="files supplied by pre-commit")
    return parser


def _policy_from_args(args: argparse.Namespace) -> Policy:
    cli_values = (
        args.forbid
        or args.allow
        or args.max_complexity is not None
        or args.max_branches is not None
        or args.require_selected
    )
    if args.policy_file is not None:
        if cli_values or args.deny_all:
            raise PolicyConfigError("do not combine --policy-file with inline policy options")
        return load_policy_file(args.policy_file)
    if not args.forbid and not args.deny_all:
        raise PolicyConfigError("choose --forbid, --deny-all, or --policy-file")
    if args.forbid and not args.forbid[0].strip():
        raise PolicyConfigError("--forbid requires at least one selector")
    if args.forbid and args.allow:
        raise PolicyConfigError("--allow is only valid with --deny-all")
    if args.deny_all and args.allow == [] and args.require_selected:
        raise PolicyConfigError("--require-selected is only valid with --forbid")
    try:
        rules = parse_selectors(args.forbid)
        allow = parse_selectors(args.allow)
    except ValueError as error:
        raise PolicyConfigError(str(error)) from error
    if "ALL" in allow:
        raise PolicyConfigError("--allow cannot contain the ALL selector")
    if args.forbid and not rules:
        raise PolicyConfigError("--forbid requires at least one selector")
    return Policy(
        mode="forbid" if args.forbid else "deny-all",
        rules=rules,
        allow=allow,
        max_complexity=args.max_complexity,
        max_branches=args.max_branches,
        require_selected=args.require_selected,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command != "check":  # pragma: no cover - argparse enforces this
        parser.error(f"unsupported command: {args.command}")
    try:
        policy = _policy_from_args(args)
    except PolicyConfigError as error:
        parser.error(str(error))
    violations = PolicyChecker(policy).check_files(tuple(args.filenames))
    for violation in violations:
        print(violation.format())
    return int(bool(violations))
