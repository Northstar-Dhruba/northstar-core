"""Tests for the held quantity of one listed asset in a paper portfolio."""

from __future__ import annotations

from decimal import Decimal

import pytest

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    Currency,
    ExchangeCode,
    Price,
    Quantity,
    Symbol,
)
from northstar_core.paper_trading import InvalidPositionError, Position

_USD = Currency("USD")
_LISTING = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))


def _position(**overrides: object) -> Position:
    values: dict[str, object] = {
        "listing_reference": _LISTING,
        "quantity": Quantity("10"),
        "average_price": Price("100", _USD),
    }
    values.update(overrides)
    return Position(**values)


def test_position_preserves_every_member() -> None:
    position = _position()

    assert position.listing_reference == _LISTING
    assert position.quantity == Quantity("10")
    assert position.average_price == Price("100", _USD)


def test_fractional_holdings_are_accepted() -> None:
    assert _position(quantity=Quantity("0.5")).quantity.value == Decimal("0.5")


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("listing_reference", "listing reference cannot be None"),
        ("quantity", "quantity cannot be None"),
        ("average_price", "average price cannot be None"),
    ],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidPositionError, match=message):
        _position(**{field: None})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("listing_reference", "AAPL@NASDAQ", "must be a ListingReference"),
        ("quantity", 10, "must be a Quantity"),
        ("quantity", Decimal("10"), "must be a Quantity"),
        ("average_price", 100, "must be a Price"),
        ("average_price", Decimal("100"), "must be a Price"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidPositionError, match=message):
        _position(**{field: value})


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidPositionError, ValidationError)
    with pytest.raises(ValidationError):
        _position(quantity=None)


def test_zero_quantity_is_rejected() -> None:
    """A flat holding is the absence of a Position, never a zero one."""
    with pytest.raises(InvalidPositionError, match="quantity must be greater than zero"):
        _position(quantity=Quantity("0"))


def test_zero_quantity_is_rejected_in_every_spelling() -> None:
    for zero in ("0", "0.0", "0.0000"):
        with pytest.raises(InvalidPositionError, match="quantity must be greater than zero"):
            _position(quantity=Quantity(zero))


def test_zero_average_price_is_rejected() -> None:
    with pytest.raises(InvalidPositionError, match="average price must be greater than zero"):
        _position(average_price=Price("0", _USD))


def test_smallest_positive_values_are_accepted() -> None:
    position = _position(quantity=Quantity("0.00000001"), average_price=Price("0.01", _USD))

    assert position.quantity.value > 0
    assert position.average_price.amount > 0


def test_position_is_long_only_by_construction() -> None:
    """Quantity is magnitude-only, so a short holding is unrepresentable."""
    from northstar_core.foundation.exceptions.validation import InvalidQuantityError

    with pytest.raises(InvalidQuantityError):
        Quantity("-10")


def test_position_carries_no_valuation_or_leverage_meaning() -> None:
    position = _position()

    for absent in (
        "market_value",
        "unrealised_pnl",
        "unrealized_pnl",
        "realised_pnl",
        "leverage",
        "margin",
        "point_in_time",
    ):
        assert not hasattr(position, absent)


def test_position_is_immutable() -> None:
    position = _position()

    with pytest.raises(AttributeError):
        position.quantity = Quantity("20")
    with pytest.raises(AttributeError):
        position.average_price = Price("200", _USD)


def test_equivalent_positions_compare_and_hash_equal() -> None:
    assert _position() == _position()
    assert hash(_position()) == hash(_position())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("listing_reference", ListingReference(Symbol("MSFT"), ExchangeCode("NASDAQ"))),
        ("quantity", Quantity("11")),
        ("average_price", Price("101", _USD)),
        ("average_price", Price("100", Currency("EUR"))),
    ],
)
def test_positions_differing_in_any_member_are_not_equal(field: str, value: object) -> None:
    assert _position() != _position(**{field: value})


def test_position_is_usable_as_a_dictionary_key() -> None:
    assert {_position(): "kept"}[_position()] == "kept"


def test_string_and_repr_forms_expose_the_holding() -> None:
    position = _position()

    assert str(position) == "AAPL@NASDAQ 10 @ 100 USD"
    assert repr(position).startswith("Position(listing_reference=")
