"""Tests for the paper-trading execution direction vocabulary."""

from __future__ import annotations

import pytest

from northstar_core.paper_trading import OrderSide


def test_vocabulary_is_exactly_buy_and_sell() -> None:
    assert [side.value for side in OrderSide] == ["BUY", "SELL"]


def test_there_is_no_hold_member() -> None:
    """HOLD is a recommendation outcome, never an execution direction."""
    assert not hasattr(OrderSide, "HOLD")
    assert "HOLD" not in OrderSide.__members__
    assert "HOLD" not in {side.value for side in OrderSide}


def test_hold_cannot_be_constructed() -> None:
    with pytest.raises(ValueError, match="HOLD"):
        OrderSide("HOLD")


@pytest.mark.parametrize("value", ["hold", "Hold", "", "BUY_TO_OPEN", "SHORT", "COVER"])
def test_unknown_directions_are_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        OrderSide(value)


def test_lowercase_is_not_silently_accepted() -> None:
    """The vocabulary is closed and exact; normalization is not this value's job."""
    with pytest.raises(ValueError):
        OrderSide("buy")


def test_members_are_constructible_from_their_own_value() -> None:
    assert OrderSide("BUY") is OrderSide.BUY
    assert OrderSide("SELL") is OrderSide.SELL


def test_members_compare_equal_to_their_string_value() -> None:
    assert OrderSide.BUY == "BUY"
    assert OrderSide.SELL == "SELL"


def test_members_are_strings() -> None:
    assert isinstance(OrderSide.BUY, str)
    assert f"{OrderSide.BUY}" == "BUY"


def test_members_are_distinct_and_hashable() -> None:
    assert OrderSide.BUY is not OrderSide.SELL
    assert len({OrderSide.BUY, OrderSide.SELL}) == 2


def test_a_plain_string_is_not_an_order_side() -> None:
    """Value objects type-check against OrderSide, so a bare string must not pass."""
    assert not isinstance("BUY", OrderSide)
