"""Tests for the settlement-currency value of one quote point per contract."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from decimal import ROUND_CEILING, ROUND_DOWN, ROUND_HALF_UP, Decimal, localcontext
from pathlib import Path

import pytest

import northstar_core.futures.value_objects.futures_point_value as module
from northstar_core.derivatives import QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, Money, Price
from northstar_core.futures import FuturesPointValue, InvalidFuturesPointValueError

_USD = Currency("USD")
_EUR = Currency("EUR")
_HIGH_PRECISION = "12.345678901234567890123456789012345678901234567890123"


def _point(amount: object = Decimal("50"), currency: object = _USD) -> FuturesPointValue:
    return FuturesPointValue(amount, currency)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "amount",
    ["50", "12.5", "0.00000001", _HIGH_PRECISION],
    ids=["whole", "fraction", "tiny", "precise"],
)
def test_positive_decimal_amounts_are_accepted(amount: str) -> None:
    point = _point(Decimal(amount))

    assert point.amount == Decimal(amount)
    assert point.currency == _USD


def test_high_precision_keeps_every_digit() -> None:
    assert str(_point(Decimal(_HIGH_PRECISION)).amount) == _HIGH_PRECISION


# ---------------------------------------------------------------------------
# Amount validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("amount", ["0", "0.000", "-0", "-0.0"], ids=["0", "0.000", "-0", "-0.0"])
def test_zero_in_every_spelling_is_rejected(amount: str) -> None:
    with pytest.raises(InvalidFuturesPointValueError, match="greater than zero"):
        _point(Decimal(amount))


@pytest.mark.parametrize("amount", ["-1", "-0.00000001", "-50"])
def test_negative_amounts_are_rejected(amount: str) -> None:
    with pytest.raises(InvalidFuturesPointValueError, match="greater than zero"):
        _point(Decimal(amount))


@pytest.mark.parametrize("amount", ["NaN", "sNaN", "Infinity", "-Infinity"])
def test_non_finite_amounts_are_rejected(amount: str) -> None:
    with pytest.raises(InvalidFuturesPointValueError):
        _point(Decimal(amount))


@pytest.mark.parametrize(
    "amount", [50.0, 50, True, "50", None], ids=["float", "int", "bool", "str", "none"]
)
def test_non_decimal_amounts_are_rejected(amount: object) -> None:
    with pytest.raises(InvalidFuturesPointValueError):
        _point(amount)


@pytest.mark.parametrize("currency", ["USD", None, Decimal("1")], ids=["str", "none", "decimal"])
def test_the_currency_must_be_a_currency(currency: object) -> None:
    with pytest.raises(InvalidFuturesPointValueError, match="currency"):
        _point(currency=currency)


def test_the_error_is_a_dedicated_validation_error() -> None:
    from northstar_core.foundation.exceptions.validation import (
        InvalidMoneyError,
        InvalidPriceError,
    )

    assert issubclass(InvalidFuturesPointValueError, ValidationError)
    assert not issubclass(InvalidFuturesPointValueError, (InvalidMoneyError, InvalidPriceError))


# ---------------------------------------------------------------------------
# Canonical Decimal semantics
# ---------------------------------------------------------------------------


def test_equivalent_spellings_are_one_value() -> None:
    spellings = [_point(Decimal(text)) for text in ("50", "50.0", "50.000", "5E+1")]

    assert len(set(spellings)) == 1
    assert {str(point.amount) for point in spellings} == {"50"}


def test_the_canonical_form_matches_quote_value_and_money() -> None:
    amount = Decimal("12.50")

    assert _point(amount).amount == QuoteValue(amount).value == Money(amount, _USD).amount
    assert str(_point(amount).amount) == str(QuoteValue(amount).value) == "12.5"


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
        _point(Decimal(_HIGH_PRECISION))

        assert (context.prec, context.rounding) == (6, ROUND_DOWN)


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_equal_values_compare_and_hash_equal() -> None:
    assert _point() == _point()
    assert hash(_point()) == hash(_point())
    assert _point() != _point(Decimal("50.01"))
    assert _point() != _point(currency=_EUR)


def test_the_value_is_immutable() -> None:
    point = _point()

    with pytest.raises(FrozenInstanceError):
        point.amount = Decimal("1")  # type: ignore[misc]


def test_point_values_are_not_ordered() -> None:
    with pytest.raises(TypeError):
        _ = _point() < _point(Decimal("60"))  # type: ignore[operator]


def test_a_point_value_is_neither_money_nor_price() -> None:
    assert _point() != Money(Decimal("50"), _USD)
    assert not isinstance(_point(), (Money, Price))


def test_the_string_form_states_the_unit() -> None:
    assert str(_point()) == "50 USD/point/contract"
    assert (
        repr(_point()) == "FuturesPointValue(amount=Decimal('50'), currency=Currency(value='USD'))"
    )


def test_negative_quotes_remain_valid_alongside_a_positive_point_value() -> None:
    """The point value is positive; the quotes it converts need not be."""
    assert _point().amount > 0
    assert QuoteValue(Decimal("-37.63")).value < 0
    assert QuoteValue(Decimal("0")).value == 0


# ---------------------------------------------------------------------------
# No arithmetic
# ---------------------------------------------------------------------------


def test_the_value_offers_no_arithmetic() -> None:
    for operator in ("__add__", "__sub__", "__mul__", "__rmul__", "__truediv__"):
        assert not hasattr(FuturesPointValue, operator)
    with pytest.raises(TypeError):
        _ = _point() * 2  # type: ignore[operator]


def test_the_module_imports_no_money_or_arithmetic_context() -> None:
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }

    assert not names & {"Money", "Price", "localcontext", "Context", "getcontext"}
