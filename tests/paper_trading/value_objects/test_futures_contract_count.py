"""Tests for the positive whole number of futures contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Quantity
from northstar_core.paper_trading import (
    FuturesContractCount,
    InvalidFuturesContractCountError,
)


def test_one_contract_is_accepted() -> None:
    assert FuturesContractCount(1).value == 1


def test_large_positive_count_is_accepted() -> None:
    assert FuturesContractCount(10**18).value == 10**18


def test_the_stored_value_is_an_exact_int() -> None:
    assert type(FuturesContractCount(5).value) is int


def test_zero_is_rejected() -> None:
    with pytest.raises(InvalidFuturesContractCountError, match="greater than zero"):
        FuturesContractCount(0)


@pytest.mark.parametrize("value", [-1, -5, -(10**18)])
def test_negative_counts_are_rejected(value: int) -> None:
    """Direction belongs to OrderSide; a count is never signed."""
    with pytest.raises(InvalidFuturesContractCountError, match="greater than zero"):
        FuturesContractCount(value)


@pytest.mark.parametrize("value", [True, False])
def test_bool_is_rejected(value: bool) -> None:
    """bool subclasses int, so True must be rejected by type, not by value."""
    with pytest.raises(InvalidFuturesContractCountError, match="must be an integer"):
        FuturesContractCount(value)


@pytest.mark.parametrize("value", [Decimal("1.5"), 1.5, Decimal("0.1")])
def test_fractional_values_are_rejected(value: object) -> None:
    with pytest.raises(InvalidFuturesContractCountError, match="must be an integer"):
        FuturesContractCount(value)


@pytest.mark.parametrize("value", [Decimal("2"), Decimal("2.0"), 2.0])
def test_integral_decimal_and_float_are_rejected(value: object) -> None:
    """Only int is accepted; conversion from a decimal source is the caller's job."""
    with pytest.raises(InvalidFuturesContractCountError, match="must be an integer"):
        FuturesContractCount(value)


@pytest.mark.parametrize("value", ["1", Quantity("1")])
def test_other_types_are_rejected(value: object) -> None:
    with pytest.raises(InvalidFuturesContractCountError, match="must be an integer"):
        FuturesContractCount(value)


def test_none_is_rejected() -> None:
    with pytest.raises(InvalidFuturesContractCountError, match="cannot be None"):
        FuturesContractCount(None)


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesContractCountError, ValidationError)


def test_equal_counts_compare_and_hash_equal() -> None:
    assert FuturesContractCount(3) == FuturesContractCount(3)
    assert hash(FuturesContractCount(3)) == hash(FuturesContractCount(3))
    assert FuturesContractCount(3) != FuturesContractCount(4)
    assert len({FuturesContractCount(3), FuturesContractCount(3)}) == 1


def test_counts_are_ordered_by_value() -> None:
    assert FuturesContractCount(1) < FuturesContractCount(2)


def test_count_is_not_equal_to_a_bare_int() -> None:
    assert FuturesContractCount(1) != 1


def test_count_is_immutable() -> None:
    count = FuturesContractCount(1)

    with pytest.raises(FrozenInstanceError):
        count.value = 2  # type: ignore[misc]


def test_count_defines_no_arithmetic() -> None:
    with pytest.raises(TypeError):
        FuturesContractCount(1) + FuturesContractCount(1)  # type: ignore[operator]


def test_string_forms() -> None:
    assert str(FuturesContractCount(7)) == "7"
    assert repr(FuturesContractCount(7)) == "FuturesContractCount(value=7)"
