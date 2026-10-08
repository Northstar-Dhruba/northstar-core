"""Tests for the strike of one option contract."""

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
from northstar_core.options import InvalidOptionStrikeError, OptionStrike

# A strike with more digits than any ambient precision used below.
_HIGH_PRECISION = "25000.123456789012345678901234567890123456789012345678"


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["25000", "24950.5", "0.05", "0.00000001", _HIGH_PRECISION],
    ids=["whole", "half", "tick", "tiny", "precise"],
)
def test_positive_decimal_strikes_are_accepted(value: str) -> None:
    assert OptionStrike(Decimal(value)).value == Decimal(value)


def test_high_precision_keeps_every_digit() -> None:
    assert str(OptionStrike(Decimal(_HIGH_PRECISION))) == _HIGH_PRECISION


# ---------------------------------------------------------------------------
# Positivity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["0", "0.000", "-0", "-0.0", "0E+3"])
def test_zero_in_every_spelling_is_rejected(value: str) -> None:
    with pytest.raises(InvalidOptionStrikeError, match="greater than zero"):
        OptionStrike(Decimal(value))


@pytest.mark.parametrize("value", ["-1", "-0.00000001", "-25000"])
def test_negative_strikes_are_rejected(value: str) -> None:
    with pytest.raises(InvalidOptionStrikeError, match="greater than zero"):
        OptionStrike(Decimal(value))


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_none_is_rejected() -> None:
    with pytest.raises(InvalidOptionStrikeError, match="cannot be None"):
        OptionStrike(None)


def test_a_float_is_rejected() -> None:
    """A binary float cannot hold every decimal strike exactly."""
    with pytest.raises(InvalidOptionStrikeError, match="must be a Decimal"):
        OptionStrike(25000.5)


@pytest.mark.parametrize("value", [True, False])
def test_a_bool_is_rejected(value: bool) -> None:
    """bool is an int subclass and must never pass as a strike of one."""
    with pytest.raises(InvalidOptionStrikeError, match="must be a Decimal"):
        OptionStrike(value)


@pytest.mark.parametrize(
    "value",
    [25000, "25000", b"25000", ["25000"], QuoteValue(Decimal("25000")), object()],
    ids=["int", "str", "bytes", "list", "quote", "object"],
)
def test_non_decimal_inputs_are_rejected(value: object) -> None:
    """The caller, not this value, owns conversion from a provider's spelling."""
    with pytest.raises(InvalidOptionStrikeError, match="must be a Decimal"):
        OptionStrike(value)


@pytest.mark.parametrize("value", ["NaN", "-NaN", "sNaN", "Infinity", "-Infinity"])
def test_non_finite_values_are_rejected(value: str) -> None:
    with pytest.raises(InvalidOptionStrikeError, match="must be finite"):
        OptionStrike(Decimal(value))


def test_the_error_is_a_dedicated_validation_error() -> None:
    assert issubclass(InvalidOptionStrikeError, ValidationError)
    assert not issubclass(InvalidOptionStrikeError, (InvalidMoneyError, InvalidPriceError))
    with pytest.raises(ValidationError):
        OptionStrike(None)


# ---------------------------------------------------------------------------
# Canonical Decimal semantics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("spelling", ["25000", "25000.0", "25000.000", "2.5E+4", "250E+2"])
def test_equivalent_spellings_are_one_value(spelling: str) -> None:
    assert OptionStrike(Decimal(spelling)) == OptionStrike(Decimal("25000"))
    assert hash(OptionStrike(Decimal(spelling))) == hash(OptionStrike(Decimal("25000")))


def test_the_canonical_form_is_plain_notation() -> None:
    assert str(OptionStrike(Decimal("2.5E+4"))) == "25000"
    assert str(OptionStrike(Decimal("24950.50"))) == "24950.5"
    assert str(OptionStrike(Decimal("1E+2"))) == "100"


def test_the_canonical_form_matches_the_shared_derivative_values() -> None:
    value = Decimal("24950.50")

    assert OptionStrike(value).value == QuoteValue(value).value
    assert str(OptionStrike(value)) == str(QuoteValue(value)) == "24950.5"


# ---------------------------------------------------------------------------
# Determinism under a hostile ambient context
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("precision", [6, 28, 50])
@pytest.mark.parametrize("rounding", [ROUND_DOWN, ROUND_CEILING, ROUND_HALF_UP])
def test_construction_ignores_the_callers_decimal_context(precision: int, rounding: str) -> None:
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        built = [OptionStrike(Decimal(text)) for text in ("25000.000", "2.5E+4", _HIGH_PRECISION)]

    assert built == [
        OptionStrike(Decimal("25000")),
        OptionStrike(Decimal("25000")),
        OptionStrike(Decimal(_HIGH_PRECISION)),
    ]
    assert str(built[2]) == _HIGH_PRECISION


def test_normalize_really_would_have_lost_those_digits() -> None:
    """Pins why the strike uses the context-independent canonicalization."""
    with localcontext() as context:
        context.prec = 6

        assert str(Decimal(_HIGH_PRECISION).normalize()) == "25000.1"


def test_construction_does_not_disturb_the_callers_context() -> None:
    before = getcontext()
    precision, rounding, flags = before.prec, before.rounding, dict(before.flags)

    OptionStrike(Decimal(_HIGH_PRECISION))
    OptionStrike(Decimal("25000"))

    after = getcontext()
    assert (after.prec, after.rounding) == (precision, rounding)
    assert dict(after.flags) == flags


def test_no_inexact_or_rounded_flag_is_raised() -> None:
    """A raised flag would mean some operation consulted the context."""
    with localcontext() as context:
        context.prec = 6
        context.clear_flags()

        OptionStrike(Decimal(_HIGH_PRECISION))

        assert not any(context.flags.values())


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_distinct_strikes_are_unequal() -> None:
    assert OptionStrike(Decimal("25000")) != OptionStrike(Decimal("25050"))


def test_it_is_usable_as_a_dictionary_key() -> None:
    assert {OptionStrike(Decimal("25000.0")): "atm"}[OptionStrike(Decimal("25000"))] == "atm"


def test_strikes_order_numerically() -> None:
    strikes = [OptionStrike(Decimal(text)) for text in ("25000", "9950", "24950.5", "100")]

    assert [str(strike) for strike in sorted(strikes)] == ["100", "9950", "24950.5", "25000"]
    assert OptionStrike(Decimal("9950")) < OptionStrike(Decimal("25000"))


def test_ordering_agrees_with_equality_for_equivalent_spellings() -> None:
    assert not OptionStrike(Decimal("25000.0")) < OptionStrike(Decimal("25000"))
    assert OptionStrike(Decimal("25000.0")) <= OptionStrike(Decimal("25000"))


def test_the_strike_is_immutable() -> None:
    strike = OptionStrike(Decimal("25000"))

    with pytest.raises(FrozenInstanceError):
        strike.value = Decimal("1")  # type: ignore[misc]


def test_string_and_repr_forms() -> None:
    strike = OptionStrike(Decimal("24950.50"))

    assert str(strike) == "24950.5"
    assert repr(strike) == "OptionStrike(value=Decimal('24950.5'))"


def test_only_the_decimal_is_stored() -> None:
    assert set(OptionStrike.__slots__) == {"value"}


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------


def test_the_strike_makes_no_currency_or_unit_claim() -> None:
    """A NIFTY strike is index points, not rupees."""
    strike = OptionStrike(Decimal("25000"))

    for absent in ("currency", "unit", "quotation_unit", "tick_size", "multiplier", "lot_size"):
        assert not hasattr(strike, absent)


def test_a_strike_is_not_a_quote_price_or_money() -> None:
    strike = OptionStrike(Decimal("25000"))
    inr = Currency("INR")

    assert not isinstance(strike, (QuoteValue, Price, Money))
    assert strike != QuoteValue(Decimal("25000"))
    assert strike != Price(Decimal("25000"), inr)
    assert strike != Money(Decimal("25000"), inr)


def test_strikes_offer_no_arithmetic() -> None:
    for operator in ("__add__", "__sub__", "__mul__", "__rmul__", "__truediv__", "__neg__"):
        assert not hasattr(OptionStrike, operator)
    with pytest.raises(TypeError):
        _ = OptionStrike(Decimal("1")) + OptionStrike(Decimal("1"))  # type: ignore[operator]
    with pytest.raises(TypeError):
        _ = OptionStrike(Decimal("1")) * 2  # type: ignore[operator]
