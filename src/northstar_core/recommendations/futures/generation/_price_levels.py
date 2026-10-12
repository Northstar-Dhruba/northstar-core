"""Exact price-level arithmetic for recommendation generation (ADR-018).

Every level decision is made in exact rational arithmetic: Decimal inputs are
converted to Fraction without loss, the movement unit is the exact quotient of
the total absolute close-to-close change by the number of changes, and levels
are aligned to the price increment with a true floor or ceiling. Nothing here
uses binary floating point, and nothing rounds except the documented alignment.

Floor and ceiling are mathematical, not truncation toward zero, so a level of
-0.03 floors to -0.05 and ceils to 0 on an increment of 0.05.

An aligned level is an integer multiple of the increment. It is converted back
to Decimal under a copy of ``_EXACT_CONTEXT``, which traps inexact and rounded
results: a value that cannot be represented exactly in twenty-eight significant
digits raises ``decimal.Inexact`` or ``decimal.Rounded`` rather than being
rounded.

Display values -- the movement unit and the reward-to-risk ratio -- are rounded
under a copy of ``_DISPLAY_CONTEXT`` (28 digits, round-half-even, as the
directional signal uses). They are never used to decide anything, and are
rendered in fixed-point notation, never scientific.

Every Decimal operation that can signal runs inside ``localcontext`` on a fresh
copy of one of the two module contexts, as the directional signal does. The
module contexts are configuration only: no calculation records a flag on them,
and the caller's own context is restored unchanged afterwards.

This module is internal to the generation package and is not exported. It
defines no classes, so the package's class set stays exactly its public surface.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Context, Decimal, Inexact, Rounded, localcontext
from fractions import Fraction

from northstar_core.recommendations.futures.value_objects import TradeDirection

_DISPLAY_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)
_EXACT_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN, traps=[Inexact, Rounded])


def to_decimal(value: Fraction) -> Decimal:
    """Convert a rational with a terminating expansion to an exact Decimal.

    Raises ``decimal.Inexact`` or ``decimal.Rounded`` if the value cannot be
    represented exactly in twenty-eight significant digits.
    """
    with localcontext(_EXACT_CONTEXT) as context:
        return context.divide(Decimal(value.numerator), Decimal(value.denominator))


def floor_to(value: Fraction, increment: Fraction) -> Fraction:
    """Return the greatest multiple of ``increment`` not above ``value``."""
    return (value // increment) * increment


def ceil_to(value: Fraction, increment: Fraction) -> Fraction:
    """Return the least multiple of ``increment`` not below ``value``."""
    return -((-value) // increment) * increment


def total_absolute_change(closes: tuple[Decimal, ...], changes: int) -> Decimal | None:
    """Return the exact sum of the trailing ``changes`` absolute close-to-close changes.

    Returns None when fewer than ``changes + 1`` closes are available.
    """
    if len(closes) < changes + 1:
        return None
    window = [Fraction(close) for close in closes[-(changes + 1) :]]
    total = sum(
        (abs(later - earlier) for earlier, later in zip(window, window[1:], strict=False)),
        Fraction(0),
    )
    return to_decimal(total)


def entry_bounds(
    reference: Decimal,
    unit: Fraction,
    entry_multiplier: Decimal,
    increment: Decimal,
) -> tuple[Fraction, Fraction]:
    """Return the inward-aligned (low, high) entry bounds; low may exceed high."""
    step = Fraction(increment)
    half_width = Fraction(entry_multiplier) * unit
    low = ceil_to(Fraction(reference) - half_width, step)
    high = floor_to(Fraction(reference) + half_width, step)
    return low, high


def stop_and_target(
    direction: TradeDirection,
    entry_low: Fraction,
    entry_high: Fraction,
    unit: Fraction,
    stop_multiplier: Decimal,
    target_multiplier: Decimal,
    increment: Decimal,
) -> tuple[Fraction, Fraction]:
    """Return the aligned (stop, target) for a direction.

    The stop is aligned away from the entry zone and the target toward it, so
    alignment can only increase risk and reduce reward.
    """
    step = Fraction(increment)
    stop_distance = Fraction(stop_multiplier) * unit
    target_distance = Fraction(target_multiplier) * unit
    if direction is TradeDirection.LONG:
        return (
            floor_to(entry_low - stop_distance, step),
            floor_to(entry_high + target_distance, step),
        )
    return (
        ceil_to(entry_high + stop_distance, step),
        ceil_to(entry_low - target_distance, step),
    )


def worst_entry_reward_and_risk(
    direction: TradeDirection,
    entry_low: Decimal,
    entry_high: Decimal,
    stop: Decimal,
    target: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """Return (worst entry, reward, risk) measured from the worst entry in the zone.

    Reward or risk is zero or negative when a level does not lie strictly on
    its side of the zone; the caller decides what that means.
    """
    if direction is TradeDirection.LONG:
        worst = entry_high
        reward = Fraction(target) - Fraction(worst)
        risk = Fraction(worst) - Fraction(stop)
    else:
        worst = entry_low
        reward = Fraction(worst) - Fraction(target)
        risk = Fraction(stop) - Fraction(worst)
    return worst, to_decimal(reward), to_decimal(risk)


def meets_minimum(reward: Decimal, risk: Decimal, minimum: Decimal) -> bool:
    """Return whether ``reward >= minimum * risk``, compared exactly."""
    return Fraction(reward) >= Fraction(minimum) * Fraction(risk)


def display_quotient(numerator: Decimal, denominator: Decimal) -> Decimal:
    """Return ``numerator / denominator`` rounded for display only."""
    with localcontext(_DISPLAY_CONTEXT) as context:
        return context.divide(numerator, denominator)


def is_exact_quotient(display: Decimal, numerator: Decimal, denominator: Decimal) -> bool:
    """Return whether a displayed quotient is exactly ``numerator / denominator``."""
    return Fraction(display) == Fraction(numerator) / Fraction(denominator)


def fixed_point(value: Decimal) -> str:
    """Render a Decimal in plain fixed-point notation, digit for digit and sign intact.

    Formatting without a precision never rounds and never consults a context, so
    1E-7 renders as 0.0000001 and every stored digit is kept.
    """
    return format(value, "f")
