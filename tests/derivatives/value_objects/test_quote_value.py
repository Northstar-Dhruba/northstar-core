"""Tests for the signed market quotation value."""

from __future__ import annotations

from decimal import Decimal, getcontext, localcontext

import pytest

from northstar_core.derivatives import InvalidQuoteValueError, QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError

# A quotation with more digits than any ambient precision used below.
_HIGH_PRECISION = "1.2345678901234567890123456789012345678901234567890123"


# ---------------------------------------------------------------------------
# Sign
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["5432.25", "118.5", "78.42", "2650.40", "0.0001"])
def test_positive_quotations_are_accepted(value: str) -> None:
    assert QuoteValue(Decimal(value)).value == Decimal(value)


def test_zero_is_a_valid_quotation() -> None:
    assert QuoteValue(Decimal("0")).value == Decimal("0")


def test_a_negative_settlement_is_representable() -> None:
    """WTI crude settled at -37.63 on 20 April 2020; Price could not hold it."""
    quote = QuoteValue(Decimal("-37.63"))

    assert quote.value == Decimal("-37.63")
    assert quote.value < 0
    assert str(quote) == "-37.63"


@pytest.mark.parametrize("value", ["-0.01", "-1", "-37.63", "-1000.5"])
def test_negative_quotations_are_accepted(value: str) -> None:
    assert QuoteValue(Decimal(value)).value == Decimal(value)


def test_negative_zero_is_folded_to_zero() -> None:
    quote = QuoteValue(Decimal("-0.000"))

    assert quote == QuoteValue(Decimal("0"))
    assert str(quote) == "0"


# ---------------------------------------------------------------------------
# Accepted input forms
# ---------------------------------------------------------------------------


def test_integers_and_strings_are_accepted() -> None:
    assert QuoteValue(5432).value == Decimal("5432")
    assert QuoteValue("-37.63").value == Decimal("-37.63")
    assert QuoteValue("  118.5  ").value == Decimal("118.5")


def test_a_fractional_bond_quotation_is_held_exactly() -> None:
    """ZB 118 and 16.5 thirty-seconds is exact in Decimal, not in binary."""
    assert QuoteValue(Decimal("118.515625")).value == Decimal("118.515625")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_none_is_rejected() -> None:
    with pytest.raises(InvalidQuoteValueError, match="cannot be None"):
        QuoteValue(None)


def test_a_bool_is_not_a_quotation() -> None:
    """bool is an int subclass, so it must be rejected before the int branch."""
    with pytest.raises(InvalidQuoteValueError, match="must be a numeric value"):
        QuoteValue(True)
    with pytest.raises(InvalidQuoteValueError, match="must be a numeric value"):
        QuoteValue(False)


def test_a_float_is_rejected() -> None:
    """A binary float cannot hold a thirty-second of a point exactly."""
    with pytest.raises(InvalidQuoteValueError, match="must not be a float"):
        QuoteValue(37.63)


@pytest.mark.parametrize("value", [b"1", ["1"], {"v": 1}, (1,), object()])
def test_non_numeric_values_are_rejected(value: object) -> None:
    with pytest.raises(InvalidQuoteValueError, match="must be a numeric value"):
        QuoteValue(value)


@pytest.mark.parametrize("value", ["", "   ", "\t"])
def test_empty_strings_are_rejected(value: str) -> None:
    with pytest.raises(InvalidQuoteValueError, match="cannot be empty"):
        QuoteValue(value)


def test_an_unparsable_string_is_rejected() -> None:
    """A raw exchange quotation convention is not a number this value parses."""
    with pytest.raises(InvalidQuoteValueError, match="must be a numeric value"):
        QuoteValue("118-16")


@pytest.mark.parametrize("value", ["NaN", "-NaN", "sNaN", "Infinity", "-Infinity"])
def test_non_finite_values_are_rejected(value: str) -> None:
    with pytest.raises(InvalidQuoteValueError, match="must be finite"):
        QuoteValue(Decimal(value))


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidQuoteValueError, ValidationError)
    with pytest.raises(ValidationError):
        QuoteValue(None)


# ---------------------------------------------------------------------------
# Canonical equality and hashing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("spelling", ["1", "1.0", "1.000", "1E+0", "0.1E+1", "10E-1"])
def test_equivalent_spellings_are_one_value(spelling: str) -> None:
    assert QuoteValue(Decimal(spelling)) == QuoteValue(Decimal("1"))
    assert hash(QuoteValue(Decimal(spelling))) == hash(QuoteValue(Decimal("1")))


def test_equivalent_spellings_collapse_in_a_set() -> None:
    quotes = {QuoteValue(Decimal(spelling)) for spelling in ("1", "1.0", "1.000", "1E+0")}

    assert len(quotes) == 1


def test_integer_spellings_with_an_exponent_agree() -> None:
    assert QuoteValue(Decimal("1E+2")) == QuoteValue(Decimal("100"))
    assert str(QuoteValue(Decimal("1E+2"))) == "100"


def test_the_canonical_form_is_plain_notation() -> None:
    assert str(QuoteValue(Decimal("1.000"))) == "1"
    assert str(QuoteValue(Decimal("-37.6300"))) == "-37.63"
    assert str(QuoteValue(Decimal("0.00"))) == "0"


def test_distinct_quotations_are_unequal() -> None:
    assert QuoteValue(Decimal("5432.25")) != QuoteValue(Decimal("5432.5"))


def test_it_is_usable_as_a_dictionary_key() -> None:
    assert {QuoteValue(Decimal("1.00")): "one"}[QuoteValue(Decimal("1"))] == "one"


# ---------------------------------------------------------------------------
# Determinism under a hostile ambient context
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("precision", [6, 28, 50])
def test_high_precision_survives_any_ambient_precision(precision: int) -> None:
    """Decimal.normalize() would round this away; canonicalization must not."""
    with localcontext() as context:
        context.prec = precision
        quote = QuoteValue(Decimal(_HIGH_PRECISION))

    assert quote.value == Decimal(_HIGH_PRECISION)
    assert str(quote) == _HIGH_PRECISION


def test_normalize_really_would_have_lost_those_digits() -> None:
    """Pins why this value cannot reuse the Quantity canonicalization."""
    with localcontext() as context:
        context.prec = 6

        assert str(Decimal(_HIGH_PRECISION).normalize()) == "1.23457"


@pytest.mark.parametrize("precision", [6, 28, 50])
def test_construction_is_identical_at_every_precision(precision: int) -> None:
    with localcontext() as context:
        context.prec = precision
        built = [QuoteValue(Decimal(spelling)) for spelling in ("1.000", "1E+2", _HIGH_PRECISION)]

    assert built == [
        QuoteValue(Decimal("1")),
        QuoteValue(Decimal("100")),
        QuoteValue(Decimal(_HIGH_PRECISION)),
    ]


def test_construction_does_not_disturb_the_callers_context() -> None:
    before = getcontext()
    precision, rounding, flags = before.prec, before.rounding, dict(before.flags)

    QuoteValue(Decimal(_HIGH_PRECISION))
    QuoteValue(Decimal("-37.63"))

    after = getcontext()
    assert (after.prec, after.rounding) == (precision, rounding)
    assert dict(after.flags) == flags


def test_no_inexact_or_rounded_flag_is_raised() -> None:
    """A raised flag would mean some operation consulted the context."""
    with localcontext() as context:
        context.prec = 6
        context.clear_flags()

        QuoteValue(Decimal(_HIGH_PRECISION))

        assert not any(context.flags.values())


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_quotations_order_across_negative_zero_and_positive() -> None:
    assert QuoteValue(Decimal("-37.63")) < QuoteValue(Decimal("0"))
    assert QuoteValue(Decimal("0")) < QuoteValue(Decimal("5432.25"))
    assert QuoteValue(Decimal("-40")) < QuoteValue(Decimal("-37.63"))


def test_sorting_is_deterministic_with_negative_quotations() -> None:
    quotes = [
        QuoteValue(Decimal("5432.25")),
        QuoteValue(Decimal("-37.63")),
        QuoteValue(Decimal("0")),
        QuoteValue(Decimal("-40")),
    ]

    assert [str(quote) for quote in sorted(quotes)] == ["-40", "-37.63", "0", "5432.25"]


def test_ordering_agrees_with_equality_for_equivalent_spellings() -> None:
    assert not QuoteValue(Decimal("1.000")) < QuoteValue(Decimal("1"))
    assert QuoteValue(Decimal("1.000")) <= QuoteValue(Decimal("1"))


# ---------------------------------------------------------------------------
# Value semantics and scope
# ---------------------------------------------------------------------------


def test_the_quotation_is_immutable() -> None:
    quote = QuoteValue(Decimal("5432.25"))

    with pytest.raises(AttributeError):
        quote.value = Decimal("1")


def test_repr_round_trips() -> None:
    quote = QuoteValue(Decimal("-37.63"))

    assert repr(quote) == "QuoteValue(value=Decimal('-37.63'))"


def test_the_quotation_makes_no_currency_or_unit_claim() -> None:
    """ES index points are not dollars; attaching a currency would be false."""
    quote = QuoteValue(Decimal("5432.25"))

    for absent in (
        "currency",
        "unit",
        "quote_unit",
        "quotation_unit",
        "tick_size",
        "multiplier",
        "contract_multiplier",
    ):
        assert not hasattr(quote, absent)


def test_quotations_do_not_support_arithmetic() -> None:
    """Two quotations may be in different conventions; adding them is meaningless."""
    with pytest.raises(TypeError):
        QuoteValue(Decimal("1")) + QuoteValue(Decimal("1"))
    with pytest.raises(TypeError):
        QuoteValue(Decimal("1")) * Decimal("2")


def test_only_the_decimal_is_stored() -> None:
    assert set(QuoteValue.__slots__) == {"value"}
