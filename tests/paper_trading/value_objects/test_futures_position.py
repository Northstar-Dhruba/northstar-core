"""Tests for signed net exposure to one futures contract."""

from __future__ import annotations

from dataclasses import fields
from decimal import Decimal

import pytest

from northstar_core.derivatives import ExpirationDate, QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    Currency,
    ExchangeCode,
    Price,
    Quantity,
    Symbol,
)
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.paper_trading import (
    FuturesContractCount,
    FuturesPosition,
    InvalidFuturesPositionError,
)

_ES = FuturesProductReference(Symbol("ES"), ExchangeCode("CME"))
_CONTRACT = FuturesContract(_ES, ExpirationDate("2026-03-20"))


def _position(**overrides: object) -> FuturesPosition:
    values: dict[str, object] = {
        "contract": _CONTRACT,
        "net_contracts": 1,
        "average_entry": QuoteValue(Decimal("100")),
    }
    values.update(overrides)
    return FuturesPosition(**values)


# ---------------------------------------------------------------------------
# Signed exposure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("net", [1, 5])
def test_positive_net_contracts_are_long(net: int) -> None:
    position = _position(net_contracts=net)

    assert position.net_contracts == net
    assert position.is_long
    assert not position.is_short
    assert position.absolute_contracts == net


@pytest.mark.parametrize("net", [-1, -5])
def test_negative_net_contracts_are_short(net: int) -> None:
    position = _position(net_contracts=net)

    assert position.net_contracts == net
    assert position.is_short
    assert not position.is_long
    assert position.absolute_contracts == -net


def test_zero_net_contracts_is_rejected() -> None:
    """Flat means no position object."""
    with pytest.raises(InvalidFuturesPositionError, match="cannot be zero"):
        _position(net_contracts=0)


@pytest.mark.parametrize("value", [True, False])
def test_bool_net_contracts_is_rejected(value: bool) -> None:
    with pytest.raises(InvalidFuturesPositionError, match="must be an integer"):
        _position(net_contracts=value)


@pytest.mark.parametrize(
    "value", [Decimal("1"), Decimal("1.5"), 1.0, "1", Quantity("1"), FuturesContractCount(1)]
)
def test_non_int_net_contracts_is_rejected(value: object) -> None:
    with pytest.raises(InvalidFuturesPositionError, match="must be an integer"):
        _position(net_contracts=value)


# ---------------------------------------------------------------------------
# Average entry sign
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("entry", ["100", "0", "-37.63"])
def test_any_average_entry_sign_is_accepted(entry: str) -> None:
    for net in (1, -1):
        position = _position(net_contracts=net, average_entry=QuoteValue(Decimal(entry)))

        assert position.average_entry.value == Decimal(entry)


def test_a_price_is_not_an_average_entry() -> None:
    with pytest.raises(InvalidFuturesPositionError, match="must be a QuoteValue"):
        _position(average_entry=Price("100", Currency("USD")))


# ---------------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("contract", "contract cannot be None"),
        ("net_contracts", "net contracts cannot be None"),
        ("average_entry", "average entry cannot be None"),
    ],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidFuturesPositionError, match=message):
        _position(**{field: None})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("contract", _ES, "must be a FuturesContract"),
        ("contract", "ES 2026-03-20", "must be a FuturesContract"),
        ("average_entry", Decimal("100"), "must be a QuoteValue"),
        ("average_entry", 100, "must be a QuoteValue"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidFuturesPositionError, match=message):
        _position(**{field: value})


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesPositionError, ValidationError)


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_a_rebuilt_equal_contract_is_accepted_and_equal() -> None:
    rebuilt = FuturesContract(
        FuturesProductReference(Symbol("ES"), ExchangeCode("CME")), ExpirationDate("2026-03-20")
    )

    assert _position(contract=rebuilt) == _position()


def test_equivalent_positions_compare_and_hash_equal() -> None:
    assert _position() == _position()
    assert hash(_position()) == hash(_position())
    assert _position() != _position(net_contracts=-1)


def test_position_is_immutable() -> None:
    position = _position()

    with pytest.raises(AttributeError):
        position.net_contracts = 2  # type: ignore[misc]


def test_the_field_shape_carries_no_economics() -> None:
    assert [field.name for field in fields(FuturesPosition)] == [
        "contract",
        "net_contracts",
        "average_entry",
    ]


def test_string_form_shows_signed_exposure() -> None:
    assert str(_position(net_contracts=-3)) == f"{_CONTRACT} -3 @ 100"
    assert str(_position(net_contracts=3)) == f"{_CONTRACT} +3 @ 100"
