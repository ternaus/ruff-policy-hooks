import pytest

from ruff_policy.policy_config import PolicyConfigError, policy_from_selectors


def test_policy_from_selectors() -> None:
    policy = policy_from_selectors(["C901,PLR0912", "C901"])

    assert policy.rules == ("C901", "PLR0912")


def test_policy_rejects_empty_selectors() -> None:
    with pytest.raises(PolicyConfigError, match="requires at least one selector"):
        policy_from_selectors([])
