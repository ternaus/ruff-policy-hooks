from ruff_policy.selectors import (
    SelectorError,
    parse_selectors,
    selector_covers,
    selectors_intersect,
    suppression_hits_protected,
)


def test_parse_selectors_normalizes_and_deduplicates() -> None:
    assert parse_selectors(["c901, PLR0912", "C901"]) == ("C901", "PLR0912")


def test_parse_selectors_rejects_empty_items_only_when_the_whole_value_is_empty() -> None:
    assert parse_selectors(["C901, "]) == ("C901",)
    try:
        parse_selectors(["!"])
    except SelectorError as error:
        assert "invalid Ruff selector" in str(error)
    else:
        raise AssertionError("malformed selector was accepted")


def test_selector_relationships_follow_ruff_prefix_selectors() -> None:
    assert selector_covers("C9", "C901")
    assert not selector_covers("C901", "C9")
    assert selectors_intersect("C9", "C901")
    assert selectors_intersect("ALL", "PLR0912")
    assert suppression_hits_protected("C901", ("C9",))
