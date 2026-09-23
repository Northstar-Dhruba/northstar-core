"""Tests for the private deterministic directional signal.

The helper replaced arithmetic that used the caller's ambient Decimal context.
These tests pin three things: the signal policy is exactly what it was, the
result no longer depends on the caller's precision, rounding or traps, and the
equity generator produces what it produced before under the default context.
"""

from __future__ import annotations

import ast
import itertools
from decimal import (
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_HALF_EVEN,
    Decimal,
    Inexact,
    Rounded,
    getcontext,
    localcontext,
)
from pathlib import Path

import pytest

import northstar_core.strategy as strategy_package
from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.value_objects import (
    Currency,
    ExchangeCode,
    PointInTime,
    Price,
    Quantity,
    Symbol,
)
from northstar_core.strategy import AssetAnalysisGenerator, MarketObservationContext
from northstar_core.strategy import _directional_signal as signal_module
from northstar_core.strategy._directional_signal import (
    NEUTRAL_TREND,
    STRONG_BEARISH,
    STRONG_BULLISH,
    select_directional_signal,
)

_USD = Currency("USD")


def _decimals(values: list[str] | tuple[str, ...]) -> tuple[Decimal, ...]:
    return tuple(Decimal(value) for value in values)


def _signal(
    closes: list[str],
    volumes: list[str] | None = None,
    *,
    latest: str | None = None,
    previous: str | None = None,
    latest_volume: str | None = None,
) -> str:
    """Call the helper; latest/previous default to the last two closes."""
    volumes = volumes if volumes is not None else ["100"] * len(closes)
    return select_directional_signal(
        latest=Decimal(latest if latest is not None else closes[-1]),
        previous_close=Decimal(previous if previous is not None else closes[-2]),
        recent_closes=_decimals(closes),
        latest_volume=Decimal(latest_volume if latest_volume is not None else volumes[-1]),
        recent_volumes=_decimals(volumes),
    )


def _equity_context(
    closes: list[str],
    volumes: list[str],
    *,
    latest: str | None = None,
    previous: str | None = None,
    latest_volume: str | None = None,
) -> MarketObservationContext:
    return MarketObservationContext(
        listing_reference=ListingReference(Symbol("ES"), ExchangeCode("NASDAQ")),
        observed_at=PointInTime("2026-09-16T21:00:00Z"),
        latest_price=Price(latest if latest is not None else closes[-1], _USD),
        previous_close=Price(previous if previous is not None else closes[-2], _USD),
        latest_volume=Quantity(latest_volume if latest_volume is not None else volumes[-1]),
        daily_high=Price("999999", _USD),
        daily_low=Price("0", _USD),
        recent_closes=tuple(Price(close, _USD) for close in closes),
        recent_volumes=tuple(Quantity(volume) for volume in volumes),
    )


# The audit's flip case: at caller precision 6 the old arithmetic rounded both
# sums to one value and read a rising market as no trend.
_FLIP_CLOSES = ["7663.00"] * 19 + ["7663.01"]
_FLIP_VOLUMES = ["1000"] * 20


# ---------------------------------------------------------------------------
# The previous algorithm, verbatim, as the compatibility oracle
# ---------------------------------------------------------------------------


def _previous_select_signal(context: MarketObservationContext) -> str:
    """AssetAnalysisGenerator._select_signal as it was before extraction."""

    def average(values: object) -> Decimal:
        collected_values = tuple(values)
        return sum(collected_values, Decimal()) / len(collected_values)

    short_average = average(price.amount for price in context.recent_closes[-5:])
    long_average = average(price.amount for price in context.recent_closes[-20:])
    average_volume = average(volume.value for volume in context.recent_volumes[-20:])

    price_is_rising = context.latest_price > context.previous_close
    price_is_falling = context.latest_price < context.previous_close
    elevated_volume = context.latest_volume.value >= average_volume

    if price_is_rising and short_average > long_average and elevated_volume:
        return "strong bullish"
    if price_is_falling and short_average < long_average and elevated_volume:
        return "strong bearish"
    return "neutral trend"


# ---------------------------------------------------------------------------
# Precision regression
# ---------------------------------------------------------------------------


def test_the_old_arithmetic_really_did_flip_at_low_precision() -> None:
    """Guard: without this the regression below could be passing vacuously."""
    context = _equity_context(_FLIP_CLOSES, _FLIP_VOLUMES)

    with localcontext() as caller:
        caller.prec = 6
        assert _previous_select_signal(context) == NEUTRAL_TREND
    assert _previous_select_signal(context) == STRONG_BULLISH


@pytest.mark.parametrize("precision", [6, 28, 50])
def test_the_flip_case_is_strong_bullish_at_every_caller_precision(precision: int) -> None:
    with localcontext() as caller:
        caller.prec = precision
        assert _signal(_FLIP_CLOSES, _FLIP_VOLUMES) == STRONG_BULLISH


@pytest.mark.parametrize("precision", [6, 28, 50])
def test_the_equity_generator_is_strong_bullish_at_every_caller_precision(
    precision: int,
) -> None:
    context = _equity_context(_FLIP_CLOSES, _FLIP_VOLUMES)

    with localcontext() as caller:
        caller.prec = precision
        analysis = AssetAnalysisGenerator().generate(context)

    assert analysis.summarized_signals == (STRONG_BULLISH,)


@pytest.mark.parametrize("rounding", [ROUND_DOWN, ROUND_CEILING, ROUND_HALF_EVEN])
@pytest.mark.parametrize("precision", [3, 6, 28, 50])
def test_caller_rounding_does_not_reach_the_signal(precision: int, rounding: str) -> None:
    with localcontext() as caller:
        caller.prec = precision
        caller.rounding = rounding
        assert _signal(_FLIP_CLOSES, _FLIP_VOLUMES) == STRONG_BULLISH


def test_a_volume_near_tie_is_decided_identically_at_every_precision() -> None:
    """Latest volume sits 0.05 below a 1,082,661.95 average: not confirming."""
    closes = [str(7600 + index) for index in range(20)]
    volumes = ["1082662"] * 19 + ["1082661"]

    results = set()
    for precision in (3, 6, 7, 28, 50):
        with localcontext() as caller:
            caller.prec = precision
            results.add(_signal(closes, volumes))

    assert results == {NEUTRAL_TREND}


def test_repeated_calls_return_the_same_signal() -> None:
    first = _signal(_FLIP_CLOSES, _FLIP_VOLUMES)

    assert all(_signal(_FLIP_CLOSES, _FLIP_VOLUMES) == first for _ in range(50))


# ---------------------------------------------------------------------------
# Caller context isolation
# ---------------------------------------------------------------------------


def test_caller_precision_and_rounding_are_restored() -> None:
    with localcontext() as caller:
        caller.prec = 6
        caller.rounding = ROUND_DOWN
        _signal(_FLIP_CLOSES, _FLIP_VOLUMES)
        assert getcontext().prec == 6
        assert getcontext().rounding == ROUND_DOWN


def test_caller_flags_are_not_polluted_by_inexact_signal_arithmetic() -> None:
    """Thirty-digit closes force rounding inside the signal's own context."""
    closes = ["1.00000000000000000000000000001"] * 19 + ["1.00000000000000000000000000002"]

    with localcontext() as caller:
        caller.clear_flags()
        _signal(closes)
        assert not caller.flags[Inexact]
        assert not caller.flags[Rounded]


def test_the_signal_context_itself_accumulates_no_flags() -> None:
    closes = ["1.00000000000000000000000000001"] * 19 + ["1.00000000000000000000000000002"]

    _signal(closes)

    assert not any(signal_module._SIGNAL_CONTEXT.flags.values())


def test_a_caller_trapping_rounded_does_not_break_the_signal() -> None:
    """The old arithmetic would raise here: prec 6 rounds 7663.00 * 20."""
    with localcontext() as caller:
        caller.prec = 6
        caller.traps[Rounded] = True
        caller.traps[Inexact] = True
        assert _signal(_FLIP_CLOSES, _FLIP_VOLUMES) == STRONG_BULLISH


def test_the_signal_context_is_the_documented_contract() -> None:
    context = signal_module._SIGNAL_CONTEXT

    assert context.prec == 28
    assert context.rounding == ROUND_HALF_EVEN


# ---------------------------------------------------------------------------
# Policy: unchanged directions, thresholds and windows
# ---------------------------------------------------------------------------


def test_rising_confirmed_trend_with_volume_is_strong_bullish() -> None:
    assert _signal(["100"] * 15 + ["130"] * 5, previous="120") == STRONG_BULLISH


def test_falling_confirmed_trend_with_volume_is_strong_bearish() -> None:
    assert _signal(["130"] * 15 + ["100"] * 5, previous="110") == STRONG_BEARISH


@pytest.mark.parametrize(
    ("closes", "previous"),
    [
        pytest.param(["110"] * 20, "110", id="flat"),
        pytest.param(["130"] * 15 + ["100"] * 5, "90", id="rising-latest-in-a-falling-trend"),
        pytest.param(["100"] * 15 + ["130"] * 5, "140", id="falling-latest-in-a-rising-trend"),
        pytest.param(["100"] * 20, "90", id="rising-latest-with-flat-averages"),
    ],
)
def test_unconfirmed_moves_are_neutral(closes: list[str], previous: str) -> None:
    assert _signal(closes, previous=previous) == NEUTRAL_TREND


@pytest.mark.parametrize(
    ("latest_volume", "expected"),
    [
        pytest.param("99", NEUTRAL_TREND, id="below-average-does-not-confirm"),
        pytest.param("100", STRONG_BULLISH, id="equal-to-average-confirms"),
        pytest.param("101", STRONG_BULLISH, id="above-average-confirms"),
    ],
)
def test_volume_must_reach_its_average_to_confirm(latest_volume: str, expected: str) -> None:
    closes = ["100"] * 15 + ["130"] * 5

    assert _signal(closes, ["100"] * 20, previous="120", latest_volume=latest_volume) == expected


@pytest.mark.parametrize("latest_volume", ["99", "100"])
def test_volume_confirmation_applies_to_bearish_too(latest_volume: str) -> None:
    closes = ["130"] * 15 + ["100"] * 5
    expected = STRONG_BEARISH if latest_volume == "100" else NEUTRAL_TREND

    assert _signal(closes, ["100"] * 20, previous="110", latest_volume=latest_volume) == expected


def test_only_the_trailing_twenty_observations_are_read() -> None:
    closes = ["100"] * 15 + ["130"] * 5
    volumes = ["100"] * 20

    padded_closes = ["999999"] * 7 + closes
    padded_volumes = ["999999"] * 7 + volumes

    assert _signal(closes, volumes, previous="120") == STRONG_BULLISH
    assert _signal(padded_closes, padded_volumes, previous="120") == STRONG_BULLISH


def test_the_long_close_window_is_exactly_twenty() -> None:
    """closes[-20] is large enough to flip the long average if it is read."""
    closes = ["1000"] + ["100"] * 14 + ["101"] * 5

    assert _signal(closes, previous="100") == NEUTRAL_TREND
    assert _signal(closes[1:] + ["101"], previous="100") == STRONG_BULLISH


def test_the_short_close_window_is_exactly_five() -> None:
    """A four-bar short window would average 90 and read as not bullish."""
    closes = ["100"] * 15 + ["200", "90", "90", "90", "90"]

    assert _signal(closes, latest="91", previous="90") == STRONG_BULLISH


def test_the_short_close_window_is_not_six() -> None:
    """A six-bar short window would include the 10 and fall below the long average."""
    closes = ["100"] * 14 + ["10"] + ["101"] * 5

    assert _signal(closes, previous="100") == STRONG_BULLISH


def test_the_volume_window_is_exactly_twenty() -> None:
    """volumes[-20] is large enough to lift the average above 140 if it is read."""
    closes = ["100"] * 15 + ["130"] * 5
    volumes = ["1000"] + ["100"] * 18 + ["140"]

    assert _signal(closes, volumes, previous="120") == NEUTRAL_TREND


@pytest.mark.parametrize(
    "closes",
    [
        pytest.param(["100"] * 15 + ["130"] * 5, id="inside-a-rising-trend"),
        pytest.param(["130"] * 15 + ["100"] * 5, id="inside-a-falling-trend"),
    ],
)
def test_an_unchanged_latest_value_is_neither_rising_nor_falling(closes: list[str]) -> None:
    """Direction is strict: equal to the previous close confirms nothing."""
    assert _signal(closes, latest=closes[-1], previous=closes[-1]) == NEUTRAL_TREND


def test_the_equity_generator_confirms_with_latest_volume_not_the_series_tail() -> None:
    """The context's latest volume is its own fact; recent_volumes[-1] may differ."""
    closes = ["100"] * 15 + ["130"] * 5
    context = _equity_context(
        closes, ["100"] * 20, latest="130", previous="120", latest_volume="99"
    )

    assert AssetAnalysisGenerator().generate(context).summarized_signals == (NEUTRAL_TREND,)
    assert _previous_select_signal(context) == NEUTRAL_TREND


def test_the_signal_is_always_one_of_the_three_existing_strings() -> None:
    assert {STRONG_BULLISH, STRONG_BEARISH, NEUTRAL_TREND} == {
        "strong bullish",
        "strong bearish",
        "neutral trend",
    }


# ---------------------------------------------------------------------------
# Default-context compatibility with the previous equity algorithm
# ---------------------------------------------------------------------------


def _representative_equity_cases() -> list[MarketObservationContext]:
    cases = [
        # The three existing equity generator fixtures.
        _equity_context(["100"] * 15 + ["130"] * 5, ["100"] * 20, latest="130", previous="120"),
        _equity_context(["130"] * 15 + ["100"] * 5, ["100"] * 20, latest="100", previous="110"),
        _equity_context(["110"] * 20, ["100"] * 20, latest="110", previous="110"),
        # The flip case and its falling mirror.
        _equity_context(_FLIP_CLOSES, _FLIP_VOLUMES),
        _equity_context(["7663.01"] * 19 + ["7663.00"], _FLIP_VOLUMES),
    ]

    patterns = [
        [
            str(Decimal(7600 + ((index * step) % 11) - 5) + Decimal("0.25") * (index % 3))
            for index in range(length)
        ]
        for step in range(1, 15)
        for length in (20, 23)
    ]
    volume_patterns = [
        ["1082660"] * 19 + ["1082661"],
        ["1082662"] * 19 + ["1082661"],
        ["1000"] * 19 + ["999"],
        ["1000"] * 19 + ["1000"],
        ["500"] * 10 + ["1500"] * 9 + ["1100"],
    ]
    for closes, volumes in itertools.product(patterns, volume_patterns):
        volumes = ["1000"] * (len(closes) - len(volumes)) + volumes
        cases.append(_equity_context(closes, volumes))
        cases.append(_equity_context(closes, volumes, previous=closes[-1], latest=closes[-2]))
    return cases


def test_the_representative_cases_cover_every_signal() -> None:
    signals = {_previous_select_signal(case) for case in _representative_equity_cases()}

    assert signals == {STRONG_BULLISH, STRONG_BEARISH, NEUTRAL_TREND}


def test_the_generator_matches_the_previous_algorithm_under_the_default_context() -> None:
    cases = _representative_equity_cases()
    default = getcontext()
    assert default.prec == 28
    assert default.rounding == ROUND_HALF_EVEN

    for case in cases:
        analysis = AssetAnalysisGenerator().generate(case)
        assert analysis.summarized_signals == (_previous_select_signal(case),)
        assert analysis.listing_reference == case.listing_reference
        assert analysis.point_in_time == case.observed_at


# ---------------------------------------------------------------------------
# Private boundary
# ---------------------------------------------------------------------------


def test_the_helper_is_not_part_of_the_public_strategy_surface() -> None:
    for name in ("select_directional_signal", "_directional_signal", "STRONG_BULLISH"):
        assert name not in strategy_package.__all__

    for name in ("select_directional_signal", "STRONG_BULLISH", "NEUTRAL_TREND"):
        assert not hasattr(strategy_package, name)


def _tree(module: object) -> ast.Module:
    return ast.parse(Path(module.__file__).read_text(encoding="utf-8"))  # type: ignore[attr-defined]


def test_the_helper_uses_no_float_and_no_ambient_context() -> None:
    tree = _tree(signal_module)

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            assert node.id not in {"float", "getcontext", "setcontext"}
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"getcontext", "setcontext"}
        if isinstance(node, ast.Constant):
            assert not isinstance(node.value, float)


def test_every_sum_and_division_runs_inside_the_signal_context() -> None:
    tree = _tree(signal_module)
    select = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "select_directional_signal"
    )
    (with_block,) = [node for node in select.body if isinstance(node, ast.With)]
    call = with_block.items[0].context_expr

    assert isinstance(call, ast.Call)
    assert isinstance(call.func, ast.Name) and call.func.id == "localcontext"
    assert isinstance(call.args[0], ast.Name) and call.args[0].id == "_SIGNAL_CONTEXT"

    # Outside the with-block the function only compares; no arithmetic.
    for statement in select.body:
        if statement is with_block:
            continue
        for node in ast.walk(statement):
            assert not isinstance(node, ast.BinOp)
            assert not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in {"sum", "_average"}
            )


def test_the_equity_generator_no_longer_does_its_own_arithmetic() -> None:
    import northstar_core.strategy.asset_analysis_generator as generator_module

    tree = _tree(generator_module)

    for node in ast.walk(tree):
        assert not isinstance(node, ast.BinOp)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "sum"
    assert not hasattr(AssetAnalysisGenerator, "_average")
