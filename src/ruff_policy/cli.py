"""Command-line interface for the Ruff policy hook."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from . import __version__
from .policy import PolicyChecker
from .policy_config import Policy, PolicyConfigError, policy_from_selectors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ruff-policy")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check Python files for protected Ruff suppressions")
    check.add_argument(
        "--forbid", action="append", default=[], help="Ruff selectors protected from suppression when enabled"
    )
    check.add_argument("filenames", nargs="*", help="files supplied by pre-commit")
    return parser


def _policy_from_args(args: argparse.Namespace) -> Policy:
    return policy_from_selectors(args.forbid)


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
