"""Canonicalization of the numeric Value Objects must not depend on the context.

Money, Percentage, Price and Quantity once canonicalized with
Decimal.normalize(), which rounds to the ambient decimal precision. The same
input could therefore become two unequal domain values depending on who held
the context, which for values that are recorded, replayed and compared across
processes is a determinism defect.

These tests cover all four together so the guarantee cannot quietly hold for
some of them and lapse for the rest.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, getcontext, localcontext

import pytest

from northstar_core.foundation.value_objects import (
    Currency,
    Money,
    Percentage,
    Price,
    Quantity,
)

_USD = Currency("USD")

# Fifty-two significant digits: more than any ambient precision used below.
_HIGH_PRECISION = "1.2345678901234567890123456789012345678901234567890123"

# Forty significant digits, all of them meaningful either side of the point.
_LONG_FRACTION = "0.1111111111111111111111111111111111111111"

_PRECISIONS = (6, 28, 50)

# Every numeric Foundation value, reduced to "build one and show me the Decimal".
_NUMERIC_VALUE_OBJECTS: tuple[tuple[str, Callable[[object], Decimal]], ...] = (
    ("Quantity", lambda value: Quantity(value).value),
    ("Percentage", lambda value: Percentage(value).value),
    ("Price", lambda value: Price(value, _USD).amount),
    ("Money", lambda value: Money(value, _USD).amount),
)

_IDS = [name for name, _ in _NUMERIC_VALUE_OBJECTS]
_BUILDERS = [builder for _, builder in _NUMERIC_VALUE_OBJECTS]


# ---------------------------------------------------------------------------
# The defect itself
# ---------------------------------------------------------------------------


def test_normalize_would_still_lose_those_digits() -> None:
    """Pins the behaviour that made the old canonicalization wrong.

    If this ever stops holding, the rest of this module is guarding nothing.
    """
    with localcontext() as context:
        context.prec = 6

        assert str(Decimal(_HIGH_PRECISION).normalize()) == "1.23457"


@pytest.mark.parametrize("build", _BUILDERS, ids=_IDS)
@pytest.mark.parametrize("precision", _PRECISIONS)
def test_high_precision_survives_any_ambient_precision(
    build: Callable[[object], Decimal], precision: int
) -> None:
    with localcontext() as context:
        context.prec = precision
        stored = build(Decimal(_HIGH_PRECISION))

    assert stored == Decimal(_HIGH_PRECISION)
    assert str(stored) == _HIGH_PRECISION


@pytest.mark.parametrize("build", _BUILDERS, ids=_IDS)
def test_one_input_is_one_value_at_every_precision(
    build: Callable[[object], Decimal],
) -> None:
    """The defect stated plainly: prec=6 and prec=28 once disagreed."""
    stored = []
    for precision in _PRECISIONS:
        with localcontext() as context:
            context.prec = precision
            stored.append(build(Decimal(_HIGH_PRECISION)))

    assert len(set(stored)) == 1
    assert len({str(value) for value in stored}) == 1


@pytest.mark.parametrize("build", _BUILDERS, ids=_IDS)
@pytest.mark.parametrize("precision", _PRECISIONS)
def test_a_long_fraction_keeps_every_digit(
    build: Callable[[object], Decimal], precision: int
) -> None:
    with localcontext() as context:
        context.prec = precision
        stored = build(Decimal(_LONG_FRACTION))

    assert str(stored) == _LONG_FRACTION


@pytest.mark.parametrize("build", _BUILDERS, ids=_IDS)
@pytest.mark.parametrize("precision", _PRECISIONS)
def test_a_long_integer_is_not_rounded_up(
    build: Callable[[object], Decimal], precision: int
) -> None:
    """Rounding used to turn forty nines into a one followed by zeros."""
    forty_nines = "9" * 40

    with localcontext() as context:
        context.prec = precision
        stored = build(Decimal(forty_nines))

    assert str(stored) == forty_nines


# ---------------------------------------------------------------------------
# The caller's context is left alone
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("build", _BUILDERS, ids=_IDS)
def test_construction_does_not_disturb_the_callers_context(
    build: Callable[[object], Decimal],
) -> None:
    before = getcontext()
    precision, rounding, flags = before.prec, before.rounding, dict(before.flags)

    build(Decimal(_HIGH_PRECISION))
    build(Decimal("1.000"))
    build(0)

    after = getcontext()
    assert (after.prec, after.rounding) == (precision, rounding)
    assert dict(after.flags) == flags


@pytest.mark.parametrize("build", _BUILDERS, ids=_IDS)
def test_no_context_flag_is_raised(build: Callable[[object], Decimal]) -> None:
    """A raised Inexact or Rounded would prove something consulted the context."""
    with localcontext() as context:
        context.prec = 6
        context.clear_flags()

        build(Decimal(_HIGH_PRECISION))
        build(Decimal(_LONG_FRACTION))

        assert not any(context.flags.values())


# ---------------------------------------------------------------------------
# Canonical form
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("build", _BUILDERS, ids=_IDS)
@pytest.mark.parametrize("spelling", ["1", "1.0", "1.000", "1E+0", "0.1E+1", "10E-1"])
def test_equivalent_spellings_canonicalize_alike(
    build: Callable[[object], Decimal], spelling: str
) -> None:
    stored = build(Decimal(spelling))

    assert stored == Decimal("1")
    assert str(stored) == "1"


@pytest.mark.parametrize("build", _BUILDERS, ids=_IDS)
def test_integer_magnitude_is_preserved_in_plain_notation(
    build: Callable[[object], Decimal],
) -> None:
    """Stripping zeros must not reach past the decimal point."""
    assert str(build(Decimal("1E+2"))) == "100"
    assert str(build(Decimal("100"))) == "100"
    assert str(build(Decimal("1E+20"))) == "1" + "0" * 20


@pytest.mark.parametrize("build", _BUILDERS, ids=_IDS)
def test_trailing_zeros_after_the_point_are_removed(
    build: Callable[[object], Decimal],
) -> None:
    assert str(build(Decimal("12.5000"))) == "12.5"
    assert str(build(Decimal("0.000"))) == "0"


@pytest.mark.parametrize("build", _BUILDERS, ids=_IDS)
@pytest.mark.parametrize("spelling", ["-0", "-0.000", "-0.0E-5"])
def test_negative_zero_is_canonicalized_to_zero(
    build: Callable[[object], Decimal], spelling: str
) -> None:
    """A value equal to zero must not print as "-0".

    Decimal("-0") == Decimal("0") is True, so an equality assertion alone
    cannot detect this; the sign has to be inspected directly.
    """
    stored = build(Decimal(spelling))

    assert stored == Decimal("0")
    assert str(stored) == "0"
    assert not stored.is_signed()


@pytest.mark.parametrize("build", _BUILDERS, ids=_IDS)
def test_negative_zero_and_zero_are_indistinguishable(
    build: Callable[[object], Decimal],
) -> None:
    assert str(build(Decimal("-0"))) == str(build(Decimal("0")))
    assert repr(build(Decimal("-0"))) == repr(build(Decimal("0")))


# ---------------------------------------------------------------------------
# Existing validation is untouched
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("build", _BUILDERS, ids=_IDS)
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "cannot be None."),
        (True, "must be a numeric value."),
        (False, "must be a numeric value."),
        (1.5, "must not be a float."),
        (b"1", "must be a numeric value."),
        (["1"], "must be a numeric value."),
        ("", "cannot be empty."),
        ("   ", "cannot be empty."),
        ("abc", "must be a numeric value."),
        (Decimal("NaN"), "must be finite."),
        (Decimal("Infinity"), "must be finite."),
        (Decimal("-Infinity"), "must be finite."),
    ],
)
def test_rejected_inputs_keep_their_message(
    build: Callable[[object], Decimal], value: object, expected: str
) -> None:
    with pytest.raises(ValueError, match=expected.replace(".", r"\.")):
        build(value)


@pytest.mark.parametrize("build", _BUILDERS, ids=_IDS)
def test_accepted_input_types_are_unchanged(build: Callable[[object], Decimal]) -> None:
    assert build(Decimal("12.5")) == Decimal("12.5")
    assert build(12) == Decimal("12")
    assert build("12.5") == Decimal("12.5")
    assert build("  12.5  ") == Decimal("12.5")


def test_sign_rules_are_unchanged() -> None:
    """Price and Quantity still refuse negatives; Money and Percentage allow them."""
    assert Money(Decimal("-50"), _USD).amount == Decimal("-50")
    assert Percentage(Decimal("-25")).value == Decimal("-25")

    with pytest.raises(ValueError, match="cannot be negative"):
        Price(Decimal("-1"), _USD)
    with pytest.raises(ValueError, match="cannot be negative"):
        Quantity(Decimal("-1"))


def test_high_precision_negatives_are_preserved_where_permitted() -> None:
    negative = f"-{_HIGH_PRECISION}"

    with localcontext() as context:
        context.prec = 6

        assert str(Money(Decimal(negative), _USD).amount) == negative
        assert str(Percentage(Decimal(negative)).value) == negative


def test_currency_behaviour_is_untouched() -> None:
    assert Price(Decimal("1"), _USD).currency == _USD
    assert Money(Decimal("1"), _USD).currency == _USD
    assert Price(Decimal("1"), _USD) != Price(Decimal("1"), Currency("EUR"))


# ---------------------------------------------------------------------------
# Equality, hashing and ordering still follow the canonical value
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("build", _BUILDERS, ids=_IDS)
def test_precision_no_longer_decides_equality(build: Callable[[object], Decimal]) -> None:
    """Two values built under different contexts must be one value."""
    with localcontext() as context:
        context.prec = 6
        lean = build(Decimal(_HIGH_PRECISION))
    with localcontext() as context:
        context.prec = 50
        rich = build(Decimal(_HIGH_PRECISION))

    assert lean == rich
    assert hash(lean) == hash(rich)


def test_value_objects_built_under_different_precisions_are_equal() -> None:
    """The defect at the level the domain actually sees it."""
    built = []
    for precision in _PRECISIONS:
        with localcontext() as context:
            context.prec = precision
            built.append(
                (
                    Quantity(Decimal(_HIGH_PRECISION)),
                    Percentage(Decimal(_HIGH_PRECISION)),
                    Price(Decimal(_HIGH_PRECISION), _USD),
                    Money(Decimal(_HIGH_PRECISION), _USD),
                )
            )

    assert len(set(built)) == 1


def test_equivalent_spellings_share_one_hash_bucket() -> None:
    assert len({Quantity(Decimal(s)) for s in ("1", "1.0", "1.000", "1E+0")}) == 1
    assert len({Percentage(Decimal(s)) for s in ("1", "1.0", "1.000", "1E+0")}) == 1
    assert len({Price(Decimal(s), _USD) for s in ("1", "1.0", "1.000", "1E+0")}) == 1
    assert len({Money(Decimal(s), _USD) for s in ("1", "1.0", "1.000", "1E+0")}) == 1


def test_ordering_is_unchanged() -> None:
    assert Quantity(Decimal("1.0")) < Quantity(Decimal("2"))
    assert Percentage(Decimal("-25")) < Percentage(Decimal("0"))
    assert Price(Decimal("1"), _USD) < Price(Decimal("2"), _USD)
    assert Money(Decimal("-50"), _USD) < Money(Decimal("0"), _USD)


# ---------------------------------------------------------------------------
# The helper stays private
# ---------------------------------------------------------------------------


def test_the_canonicalization_helper_is_not_public_api() -> None:
    import northstar_core.foundation.value_objects as value_objects

    assert "canonical_decimal" not in value_objects.__all__
    assert not hasattr(value_objects, "canonical_decimal")
