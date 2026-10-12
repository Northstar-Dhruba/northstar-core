"""Tests for the private exact price-level arithmetic (ADR-018).

The helpers are private, but their floor and ceiling semantics for negative and
zero-crossing values, and the history-sufficiency guard that the public API
cannot reach with a valid V1 context, are behavior worth pinning directly.
"""

from __future__ import annotations

from decimal import Decimal, Inexact, Rounded, localcontext
from fractions import Fraction

import pytest

from northstar_core.recommendations.futures import TradeDirection
from northstar_core.recommendations.futures.generation import _price_levels as levels

_STEP = Fraction(Decimal("0.05"))


@pytest.mark.parametrize(
    "value, floor, ceil",
    [
        ("24377.9605", "24377.95", "24378.00"),
        ("24378.00", "24378.00", "24378.00"),
        ("0.03", "0", "0.05"),
        ("-0.03", "-0.05", "0"),
        ("-0.05", "-0.05", "-0.05"),
        ("-0.07", "-0.10", "-0.05"),
        ("-24347.76", "-24347.80", "-24347.75"),
        ("0", "0", "0"),
    ],
)
def test_floor_and_ceil_are_mathematical_for_every_sign(value: str, floor: str, ceil: str) -> None:
    exact = Fraction(Decimal(value))

    assert levels.floor_to(exact, _STEP) == Fraction(Decimal(floor))
    assert levels.ceil_to(exact, _STEP) == Fraction(Decimal(ceil))


def test_floor_is_not_truncation_toward_zero() -> None:
    assert levels.floor_to(Fraction(Decimal("-0.01")), _STEP) == Fraction(Decimal("-0.05"))


def test_total_absolute_change_is_exact() -> None:
    closes = tuple(Decimal(24000 + 20 * step) for step in range(19)) + (Decimal("24383"),)

    assert levels.total_absolute_change(closes, 19) == Decimal("383")


def test_total_absolute_change_reads_only_the_trailing_window() -> None:
    closes = (Decimal("0"), Decimal("1000")) + (Decimal("5"), Decimal("7"), Decimal("4"))

    assert levels.total_absolute_change(closes, 2) == Decimal("5")


def test_exactly_n_plus_one_closes_are_sufficient() -> None:
    closes = tuple(Decimal(step) for step in range(20))

    assert levels.total_absolute_change(closes, 19) == Decimal("19")


def test_fewer_than_n_plus_one_closes_are_insufficient_history() -> None:
    closes = tuple(Decimal(step) for step in range(19))

    assert levels.total_absolute_change(closes, 19) is None


def test_equal_closes_have_zero_total_change() -> None:
    assert levels.total_absolute_change((Decimal("24000"),) * 20, 19) == 0


def test_entry_bounds_round_inward() -> None:
    unit = Fraction(383, 19)
    low, high = levels.entry_bounds(Decimal("24383"), unit, Decimal("0.25"), Decimal("0.05"))

    assert (low, high) == (Fraction(24378), Fraction(24388))


@pytest.mark.parametrize(
    "direction, stop, target",
    [
        (TradeDirection.LONG, "24347.75", "24448.45"),
        (TradeDirection.SHORT, "24418.25", "24317.55"),
    ],
)
def test_stop_rounds_away_and_target_rounds_toward_the_zone(
    direction: TradeDirection, stop: str, target: str
) -> None:
    """Zone [24378, 24388]; kS*U = 30.2368.., kT*U = 60.4736.."""
    result = levels.stop_and_target(
        direction,
        Fraction(24378),
        Fraction(24388),
        Fraction(383, 19),
        Decimal("1.5"),
        Decimal("3"),
        Decimal("0.05"),
    )

    assert result == (Fraction(Decimal(stop)), Fraction(Decimal(target)))


def test_worst_entry_is_the_far_edge_of_the_zone_for_each_direction() -> None:
    long = levels.worst_entry_reward_and_risk(
        TradeDirection.LONG, Decimal("100"), Decimal("101"), Decimal("98"), Decimal("105")
    )
    short = levels.worst_entry_reward_and_risk(
        TradeDirection.SHORT, Decimal("100"), Decimal("101"), Decimal("103"), Decimal("96")
    )

    assert long == (Decimal("101"), Decimal("4"), Decimal("3"))
    assert short == (Decimal("100"), Decimal("4"), Decimal("3"))


def test_meets_minimum_compares_exactly() -> None:
    assert levels.meets_minimum(Decimal("60"), Decimal("40"), Decimal("1.5"))
    assert not levels.meets_minimum(
        Decimal("60"), Decimal("40"), Decimal("1.5000000000000000000000000000001")
    )


def test_a_value_that_does_not_fit_in_28_digits_is_not_rounded() -> None:
    with pytest.raises((Inexact, Rounded)):
        levels.to_decimal(Fraction(Decimal("24383.0000000000000000000000001")))


def test_arithmetic_ignores_the_callers_decimal_context() -> None:
    with localcontext() as context:
        context.prec = 3
        assert levels.total_absolute_change(
            (Decimal("24000.01"), Decimal("24383.07")), 1
        ) == Decimal("383.06")
