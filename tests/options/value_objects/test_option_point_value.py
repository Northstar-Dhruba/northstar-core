"""Tests for the settlement-currency value of one premium point per option contract."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from decimal import ROUND_CEILING, ROUND_DOWN, ROUND_HALF_UP, Decimal, localcontext
from pathlib import Path

import pytest

import northstar_core.options.value_objects.option_point_value as module
from northstar_core.foundation.exceptions.validation import (
    InvalidMoneyError,
    InvalidPriceError,
    ValidationError,
)
from northstar_core.foundation.value_objects import Currency, Money, Price
from northstar_core.futures import FuturesPointValue
from northstar_core.options import InvalidOptionPointValueError, OptionPointValue, OptionPremium

_INR = Currency("INR")
_USD = Currency("USD")
_HIGH_PRECISION = "65.123456789012345678901234567890123456789012345678901"


def _point(amount: object = Decimal("65"), currency: object = _INR) -> OptionPointValue:
    return OptionPointValue(amount, currency)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "amount",
    ["65", "75", "12.5", "0.00000001", _HIGH_PRECISION],
    ids=["lot-65", "lot-75", "fraction", "tiny", "precise"],
)
def test_positive_decimal_amounts_are_accepted(amount: str) -> None:
    point = _point(Decimal(amount))

    assert point.amount == Decimal(amount)
    assert point.currency == _INR


def test_the_members_are_preserved() -> None:
    point = _point(Decimal("65"), _INR)

    assert point.amount == Decimal("65")
    assert point.currency is _INR


# ---------------------------------------------------------------------------
# Amount validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("amount", ["0", "0.000", "-0", "-0.0"])
def test_zero_in_every_spelling_is_rejected(amount: str) -> None:
    with pytest.raises(InvalidOptionPointValueError, match="greater than zero"):
        _point(Decimal(amount))


@pytest.mark.parametrize("amount", ["-1", "-0.00000001", "-65"])
def test_negative_amounts_are_rejected(amount: str) -> None:
    with pytest.raises(InvalidOptionPointValueError, match="greater than zero"):
        _point(Decimal(amount))


@pytest.mark.parametrize("amount", ["NaN", "sNaN", "Infinity", "-Infinity"])
def test_non_finite_amounts_are_rejected(amount: str) -> None:
    with pytest.raises(InvalidOptionPointValueError, match="must be finite"):
        _point(Decimal(amount))


@pytest.mark.parametrize(
    "amount",
    [65.0, 65, True, "65", OptionPremium(Decimal("65"))],
    ids=["float", "int", "bool", "str", "premium"],
)
def test_non_decimal_amounts_are_rejected(amount: object) -> None:
    with pytest.raises(InvalidOptionPointValueError, match="must be a Decimal"):
        _point(amount)


def test_a_none_amount_is_rejected() -> None:
    with pytest.raises(InvalidOptionPointValueError, match="amount cannot be None"):
        _point(None)


# ---------------------------------------------------------------------------
# Currency validation
# ---------------------------------------------------------------------------


def test_a_none_currency_is_rejected() -> None:
    with pytest.raises(InvalidOptionPointValueError, match="currency cannot be None"):
        _point(currency=None)


@pytest.mark.parametrize("currency", ["INR", Decimal("1"), Money(Decimal("1"), _INR)])
def test_the_currency_must_be_a_currency(currency: object) -> None:
    with pytest.raises(InvalidOptionPointValueError, match="must be a Currency value"):
        _point(currency=currency)


def test_the_error_is_a_dedicated_validation_error() -> None:
    assert issubclass(InvalidOptionPointValueError, ValidationError)
    assert not issubclass(InvalidOptionPointValueError, (InvalidMoneyError, InvalidPriceError))


# ---------------------------------------------------------------------------
# Canonical Decimal semantics
# ---------------------------------------------------------------------------


def test_equivalent_spellings_are_one_value() -> None:
    spellings = [_point(Decimal(text)) for text in ("65", "65.0", "65.000", "6.5E+1")]

    assert len(set(spellings)) == 1
    assert {str(point.amount) for point in spellings} == {"65"}


@pytest.mark.parametrize("precision", [6, 28, 50])
@pytest.mark.parametrize("rounding", [ROUND_DOWN, ROUND_CEILING, ROUND_HALF_UP])
def test_construction_ignores_the_callers_decimal_context(precision: int, rounding: str) -> None:
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        built = _point(Decimal(_HIGH_PRECISION))

    assert built == _point(Decimal(_HIGH_PRECISION))
    assert str(built.amount) == _HIGH_PRECISION


def test_construction_leaves_the_callers_context_untouched() -> None:
    with localcontext() as context:
        context.prec = 6
        context.rounding = ROUND_DOWN
        context.clear_flags()
        _point(Decimal(_HIGH_PRECISION))

        assert (context.prec, context.rounding) == (6, ROUND_DOWN)
        assert not any(context.flags.values())


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_equal_values_compare_and_hash_equal() -> None:
    assert _point() == _point()
    assert hash(_point()) == hash(_point())
    assert _point() != _point(Decimal("75"))
    assert _point() != _point(currency=_USD)


def test_the_value_is_immutable() -> None:
    point = _point()

    with pytest.raises(FrozenInstanceError):
        point.amount = Decimal("1")  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        point.currency = _USD  # type: ignore[misc]


def test_point_values_are_not_ordered() -> None:
    with pytest.raises(TypeError):
        _ = _point() < _point(Decimal("75"))  # type: ignore[operator]


def test_the_field_shape_is_exactly_amount_and_currency() -> None:
    assert OptionPointValue.__slots__ == ("amount", "currency")


def test_the_string_form_states_the_premium_point_unit() -> None:
    assert str(_point()) == "65 INR/premium-point/contract"
    assert repr(_point()) == (
        "OptionPointValue(amount=Decimal('65'), currency=Currency(value='INR'))"
    )


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------


def test_an_option_point_value_is_never_a_futures_point_value() -> None:
    option = _point(Decimal("65"), _INR)
    futures = FuturesPointValue(Decimal("65"), _INR)

    assert option != futures
    assert futures != option
    assert not isinstance(option, FuturesPointValue)
    assert len({option, futures}) == 2


def test_a_point_value_is_neither_money_nor_price() -> None:
    assert _point() != Money(Decimal("65"), _INR)
    assert not isinstance(_point(), (Money, Price))


def test_the_value_carries_no_lot_or_multiplier() -> None:
    point = _point()

    for absent in ("lot_size", "lot", "multiplier", "contract_multiplier", "tick_size", "margin"):
        assert not hasattr(point, absent)


def test_the_value_offers_no_arithmetic() -> None:
    for operator in ("__add__", "__sub__", "__mul__", "__rmul__", "__truediv__"):
        assert not hasattr(OptionPointValue, operator)
    with pytest.raises(TypeError):
        _ = _point() * 2  # type: ignore[operator]


def test_the_module_imports_no_money_price_or_arithmetic_context() -> None:
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }

    assert not names & {"Money", "Price", "localcontext", "Context", "getcontext"}
