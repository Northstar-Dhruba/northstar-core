"""Tests for the right one option contract grants."""

from __future__ import annotations

import pytest

from northstar_core.options import OptionRight


def test_vocabulary_is_exactly_call_and_put() -> None:
    assert [right.value for right in OptionRight] == ["CALL", "PUT"]
    assert list(OptionRight.__members__) == ["CALL", "PUT"]


def test_members_are_constructible_from_their_own_value() -> None:
    assert OptionRight("CALL") is OptionRight.CALL
    assert OptionRight("PUT") is OptionRight.PUT


@pytest.mark.parametrize("spelling", ["CE", "PE", "C", "P"])
def test_venue_spellings_are_not_members(spelling: str) -> None:
    """CE and PE are NSE and provider vocabulary, mapped in Infrastructure."""
    assert spelling not in OptionRight.__members__
    with pytest.raises(ValueError):
        OptionRight(spelling)


@pytest.mark.parametrize("value", ["call", "Call", "", "BUY", "SELL", "STRADDLE"])
def test_unknown_rights_are_rejected(value: str) -> None:
    """The vocabulary is closed and exact; normalization is not this value's job."""
    with pytest.raises(ValueError):
        OptionRight(value)


def test_members_compare_equal_to_their_string_value() -> None:
    assert OptionRight.CALL == "CALL"
    assert OptionRight.PUT == "PUT"


def test_string_forms_are_the_canonical_value() -> None:
    assert str(OptionRight.CALL) == "CALL"
    assert f"{OptionRight.PUT}" == "PUT"
    assert isinstance(OptionRight.CALL, str)


def test_repr_is_deterministic() -> None:
    assert repr(OptionRight.CALL) == "<OptionRight.CALL: 'CALL'>"
    assert repr(OptionRight.PUT) == "<OptionRight.PUT: 'PUT'>"


def test_members_are_distinct_and_hashable() -> None:
    assert OptionRight.CALL is not OptionRight.PUT
    assert len({OptionRight.CALL, OptionRight.PUT}) == 2


def test_members_order_deterministically() -> None:
    assert sorted([OptionRight.PUT, OptionRight.CALL]) == [OptionRight.CALL, OptionRight.PUT]


def test_a_plain_string_is_not_an_option_right() -> None:
    """Contracts type-check against OptionRight, so a bare string must not pass."""
    assert not isinstance("CALL", OptionRight)


def test_the_right_carries_no_style_or_direction() -> None:
    for absent in ("exercise_style", "settlement", "is_long", "side", "moneyness"):
        assert not hasattr(OptionRight.CALL, absent)
