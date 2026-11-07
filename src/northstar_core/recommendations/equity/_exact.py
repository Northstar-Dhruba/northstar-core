"""Exact arithmetic shared by the equity recommendation package (ADR-020).

Every decision is made in exact rational arithmetic: Decimal inputs become
Fraction without loss, levels are aligned to the price increment with a true
floor or ceiling, and nothing uses binary floating point.

A result is turned back into a Decimal only under a copy of ``_EXACT_CONTEXT``,
which traps inexact and rounded results: a value that cannot be represented
exactly in twenty-eight significant digits gives ``None``, and the caller
fails closed rather than rounding.

Decimals are canonicalized without consulting any decimal context, as
Foundation's numeric values are: trailing fractional zeros are removed, the
spelling is plain notation, and negative zero becomes zero. So ``1.50`` and
``1.5`` are one value with one canonical text.

This module is internal to the equity package and is not exported. It defines
no classes.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Context, Decimal, Inexact, Rounded, localcontext
from fractions import Fraction

_EXACT_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN, traps=[Inexact, Rounded])


def canonical(value: Decimal) -> Decimal:
    """Return the canonical spelling of a finite Decimal, digit for digit."""
    sign, digits, exponent = value.as_tuple()
    coefficient = list(digits)
    assert isinstance(exponent, int)
    while exponent < 0 and coefficient and coefficient[-1] == 0:
        coefficient.pop()
        exponent += 1
    if not any(coefficient):
        sign, coefficient, exponent = 0, [0], 0
    return Decimal(format(Decimal((sign, tuple(coefficient), exponent)), "f"))


def text(value: Decimal) -> str:
    """Return a Decimal's canonical text."""
    return format(canonical(value), "f")


def require_decimal(
    value: object,
    subject: str,
    error: type[ValueError],
    *,
    allow_zero: bool,
    below_one: bool = False,
    at_most_one: bool = False,
) -> Decimal:
    """Return ``value`` canonicalized, or raise ``error``.

    Only a finite Decimal is accepted: a float, int, str or bool is refused
    rather than converted, so no value changes on the way in.
    """
    if isinstance(value, bool) or not isinstance(value, Decimal):
        raise error(f"{subject} must be a Decimal.")
    if not value.is_finite():
        raise error(f"{subject} must be finite.")
    if value < 0 or (value == 0 and not allow_zero):
        raise error(
            f"{subject} must be {'zero or greater' if allow_zero else 'greater than zero'}."
        )
    if below_one and value >= 1:
        raise error(f"{subject} must be less than one.")
    if at_most_one and value > 1:
        raise error(f"{subject} must not exceed one.")
    return canonical(value)


def floor_to(value: Fraction, increment: Fraction) -> Fraction:
    """Return the greatest multiple of ``increment`` not above ``value``."""
    return (value // increment) * increment


def ceil_to(value: Fraction, increment: Fraction) -> Fraction:
    """Return the least multiple of ``increment`` not below ``value``."""
    return -((-value) // increment) * increment


def to_decimal(value: Fraction) -> Decimal | None:
    """Return ``value`` as an exact canonical Decimal, or None if it is not representable."""
    try:
        with localcontext(_EXACT_CONTEXT) as context:
            exact = context.divide(Decimal(value.numerator), Decimal(value.denominator))
    except (Inexact, Rounded):
        return None
    return canonical(exact)


def is_multiple(value: Decimal, increment: Decimal) -> bool:
    """Return whether ``value`` is an exact multiple of ``increment``."""
    return (Fraction(value) / Fraction(increment)).denominator == 1
