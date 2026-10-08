"""Tests for the observed premium of one option contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import ROUND_CEILING, ROUND_DOWN, ROUND_HALF_UP, Decimal, getcontext, localcontext

import pytest

from northstar_core.derivatives import QuoteValue
from northstar_core.foundation.exceptions.validation import (
    InvalidMoneyError,
    InvalidPriceError,
    ValidationError,
)
from northstar_core.foundation.value_objects import Currency, Money, Price
from northstar_core.options import InvalidOptionPremiumError, OptionPremium, OptionStrike

# A premium with more digits than any ambient precision used below.
_HIGH_PRECISION = "182.35123456789012345678901234567890123456789012345678"


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["182.35", "0.05", "1", "25000", "0.00000001", _HIGH_PRECISION],
    ids=["typical", "tick", "one", "deep", "tiny", "precise"],
)
def test_positive_decimal_premiums_are_accepted(value: str) -> None:
    assert OptionPremium(Decimal(value)).value == Decimal(value)


@pytest.mark.parametrize("value", ["0", "0.00", "-0", "-0.00", "0E+3"])
def test_zero_in_every_spelling_is_a_valid_premium(value: str) -> None:
    """An option that expires worthless is worth exactly zero."""
    premium = OptionPremium(Decimal(value))

    assert premium == OptionPremium(Decimal("0"))
    assert str(premium) == "0"
    assert not premium.value.is_signed()


def test_high_precision_keeps_every_digit() -> None:
    assert str(OptionPremium(Decimal(_HIGH_PRECISION))) == _HIGH_PRECISION


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["-0.01", "-0.00000001", "-1", "-182.35"])
def test_negative_premiums_are_rejected(value: str) -> None:
    with pytest.raises(InvalidOptionPremiumError, match="cannot be negative"):
        OptionPremium(Decimal(value))


@pytest.mark.parametrize("value", ["NaN", "-NaN", "sNaN", "Infinity", "-Infinity"])
def test_non_finite_values_are_rejected(value: str) -> None:
    with pytest.raises(InvalidOptionPremiumError, match="must be finite"):
        OptionPremium(Decimal(value))


def test_none_is_rejected() -> None:
    with pytest.raises(InvalidOptionPremiumError, match="cannot be None"):
        OptionPremium(None)


@pytest.mark.parametrize(
    "value",
    [
        182.35,
        True,
        False,
        182,
        "182.35",
        b"182.35",
        QuoteValue(Decimal("182.35")),
        OptionStrike(Decimal("182.35")),
        object(),
    ],
    ids=["float", "true", "false", "int", "str", "bytes", "quote", "strike", "object"],
)
def test_non_decimal_inputs_are_rejected(value: object) -> None:
    """The caller, not this value, owns conversion from a provider's spelling."""
    with pytest.raises(InvalidOptionPremiumError, match="must be a Decimal"):
        OptionPremium(value)


def test_the_error_is_a_dedicated_validation_error() -> None:
    assert issubclass(InvalidOptionPremiumError, ValidationError)
    assert not issubclass(InvalidOptionPremiumError, (InvalidMoneyError, InvalidPriceError))
    with pytest.raises(ValidationError):
        OptionPremium(None)


# ---------------------------------------------------------------------------
# Canonical Decimal semantics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("spelling", ["182.35", "182.350", "182.3500", "1.8235E+2", "18235E-2"])
def test_equivalent_spellings_are_one_value(spelling: str) -> None:
    assert OptionPremium(Decimal(spelling)) == OptionPremium(Decimal("182.35"))
    assert hash(OptionPremium(Decimal(spelling))) == hash(OptionPremium(Decimal("182.35")))


def test_the_canonical_form_is_plain_notation() -> None:
    assert str(OptionPremium(Decimal("1.8235E+2"))) == "182.35"
    assert str(OptionPremium(Decimal("1E+2"))) == "100"
    assert str(OptionPremium(Decimal("0.0500"))) == "0.05"


@pytest.mark.parametrize("precision", [6, 28, 50])
@pytest.mark.parametrize("rounding", [ROUND_DOWN, ROUND_CEILING, ROUND_HALF_UP])
def test_construction_ignores_the_callers_decimal_context(precision: int, rounding: str) -> None:
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        built = [OptionPremium(Decimal(text)) for text in ("182.350", "-0.00", _HIGH_PRECISION)]

    assert built == [
        OptionPremium(Decimal("182.35")),
        OptionPremium(Decimal("0")),
        OptionPremium(Decimal(_HIGH_PRECISION)),
    ]
    assert str(built[2]) == _HIGH_PRECISION


def test_construction_does_not_disturb_the_callers_context() -> None:
    before = getcontext()
    precision, rounding, flags = before.prec, before.rounding, dict(before.flags)

    OptionPremium(Decimal(_HIGH_PRECISION))
    OptionPremium(Decimal("-0.00"))

    after = getcontext()
    assert (after.prec, after.rounding) == (precision, rounding)
    assert dict(after.flags) == flags


def test_no_inexact_or_rounded_flag_is_raised() -> None:
    """A raised flag would mean some operation consulted the context."""
    with localcontext() as context:
        context.prec = 6
        context.clear_flags()

        OptionPremium(Decimal(_HIGH_PRECISION))

        assert not any(context.flags.values())


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_distinct_premiums_are_unequal() -> None:
    assert OptionPremium(Decimal("182.35")) != OptionPremium(Decimal("182.4"))


def test_it_is_usable_as_a_dictionary_key() -> None:
    assert {OptionPremium(Decimal("0.0")): "worthless"}[OptionPremium(Decimal("0"))] == "worthless"


def test_premiums_order_numerically() -> None:
    premiums = [OptionPremium(Decimal(text)) for text in ("182.35", "0", "9.5", "100")]

    assert [str(premium) for premium in sorted(premiums)] == ["0", "9.5", "100", "182.35"]
    assert OptionPremium(Decimal("9.5")) < OptionPremium(Decimal("100"))


def test_ordering_agrees_with_equality_for_equivalent_spellings() -> None:
    assert not OptionPremium(Decimal("182.350")) < OptionPremium(Decimal("182.35"))
    assert OptionPremium(Decimal("182.350")) <= OptionPremium(Decimal("182.35"))


def test_the_premium_is_immutable() -> None:
    premium = OptionPremium(Decimal("182.35"))

    with pytest.raises(FrozenInstanceError):
        premium.value = Decimal("1")  # type: ignore[misc]


def test_string_and_repr_forms() -> None:
    premium = OptionPremium(Decimal("182.350"))

    assert str(premium) == "182.35"
    assert repr(premium) == "OptionPremium(value=Decimal('182.35'))"


def test_only_the_decimal_is_stored() -> None:
    assert OptionPremium.__slots__ == ("value",)


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------


def test_the_premium_makes_no_currency_or_unit_claim() -> None:
    premium = OptionPremium(Decimal("182.35"))

    for absent in ("currency", "unit", "point_value", "lot_size", "multiplier", "tick_size"):
        assert not hasattr(premium, absent)


def test_a_premium_is_not_a_strike_quote_price_or_money() -> None:
    premium = OptionPremium(Decimal("182.35"))
    inr = Currency("INR")

    assert not isinstance(premium, (OptionStrike, QuoteValue, Price, Money))
    assert premium != OptionStrike(Decimal("182.35"))
    assert premium != QuoteValue(Decimal("182.35"))
    assert premium != Price(Decimal("182.35"), inr)
    assert premium != Money(Decimal("182.35"), inr)


def test_a_premium_does_not_order_against_a_strike() -> None:
    with pytest.raises(TypeError):
        _ = OptionPremium(Decimal("1")) < OptionStrike(Decimal("2"))  # type: ignore[operator]


def test_premiums_offer_no_arithmetic() -> None:
    for operator in ("__add__", "__sub__", "__mul__", "__rmul__", "__truediv__", "__neg__"):
        assert not hasattr(OptionPremium, operator)
    with pytest.raises(TypeError):
        _ = OptionPremium(Decimal("2")) - OptionPremium(Decimal("1"))  # type: ignore[operator]
    with pytest.raises(TypeError):
        _ = OptionPremium(Decimal("1")) * 65  # type: ignore[operator]
