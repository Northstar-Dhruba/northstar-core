"""Tests for broker-reported signed net exposure to one futures contract."""

from __future__ import annotations

from dataclasses import fields

import pytest

from northstar_core.broker_execution import (
    FuturesBrokerPosition,
    InvalidFuturesBrokerPositionError,
)
from northstar_core.derivatives import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, Symbol
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.paper_trading import FuturesPosition

_CONTRACT = FuturesContract(
    FuturesProductReference(Symbol("ES"), ExchangeCode("CME")), ExpirationDate("2026-12-18")
)


def test_a_long_position() -> None:
    position = FuturesBrokerPosition(_CONTRACT, 2)

    assert position.contract is _CONTRACT
    assert position.net_contracts == 2
    assert position.is_long and not position.is_short
    assert position.absolute_contracts == 2


def test_a_short_position() -> None:
    position = FuturesBrokerPosition(_CONTRACT, -3)

    assert position.net_contracts == -3
    assert position.is_short and not position.is_long
    assert position.absolute_contracts == 3


def test_the_field_shape_carries_no_entry_or_valuation() -> None:
    """Broker average-price conventions are deliberately not frozen yet."""
    assert [field.name for field in fields(FuturesBrokerPosition)] == ["contract", "net_contracts"]
    for name in ("average_entry", "pnl", "margin", "symbol", "broker_symbol"):
        assert not hasattr(FuturesBrokerPosition(_CONTRACT, 1), name)


def test_zero_is_rejected_because_flat_is_absent() -> None:
    with pytest.raises(InvalidFuturesBrokerPositionError, match="flat holding is absent"):
        FuturesBrokerPosition(_CONTRACT, 0)


@pytest.mark.parametrize("value", [True, False])
def test_bool_is_rejected(value: bool) -> None:
    with pytest.raises(InvalidFuturesBrokerPositionError, match="must be an integer"):
        FuturesBrokerPosition(_CONTRACT, value)


@pytest.mark.parametrize("value", [1.0, "1", object()])
def test_non_integer_net_contracts_are_rejected(value: object) -> None:
    with pytest.raises(InvalidFuturesBrokerPositionError, match="must be an integer"):
        FuturesBrokerPosition(_CONTRACT, value)


@pytest.mark.parametrize(
    ("contract", "net", "message"),
    [
        (None, 1, "contract cannot be None"),
        ("ES", 1, "must be a FuturesContract"),
        (_CONTRACT, None, "net contracts cannot be None"),
    ],
)
def test_missing_and_wrong_members_are_rejected(
    contract: object, net: object, message: str
) -> None:
    with pytest.raises(InvalidFuturesBrokerPositionError, match=message):
        FuturesBrokerPosition(contract, net)


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesBrokerPositionError, ValidationError)


def test_the_broker_position_is_not_the_paper_position() -> None:
    assert not issubclass(FuturesBrokerPosition, FuturesPosition)
    assert not issubclass(FuturesPosition, FuturesBrokerPosition)


def test_position_is_immutable() -> None:
    position = FuturesBrokerPosition(_CONTRACT, 1)

    with pytest.raises(AttributeError):
        position.net_contracts = 2  # type: ignore[misc]


def test_equivalent_positions_compare_and_hash_equal() -> None:
    assert FuturesBrokerPosition(_CONTRACT, 1) == FuturesBrokerPosition(_CONTRACT, 1)
    assert hash(FuturesBrokerPosition(_CONTRACT, -1)) == hash(FuturesBrokerPosition(_CONTRACT, -1))
    assert FuturesBrokerPosition(_CONTRACT, 1) != FuturesBrokerPosition(_CONTRACT, -1)


def test_string_and_repr_forms() -> None:
    assert str(FuturesBrokerPosition(_CONTRACT, 1)) == "ES@CME 2026-12-18 +1"
    assert str(FuturesBrokerPosition(_CONTRACT, -2)) == "ES@CME 2026-12-18 -2"
    assert repr(FuturesBrokerPosition(_CONTRACT, 1)) == (
        f"FuturesBrokerPosition(contract={_CONTRACT!r}, net_contracts=1)"
    )
