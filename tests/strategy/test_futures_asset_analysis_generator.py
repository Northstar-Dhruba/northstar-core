"""Tests for deterministic FuturesAssetAnalysis generation.

The generator owns no arithmetic: it unwraps a futures context and delegates to
the shared directional signal. The tests therefore pin the unwrapping (every
field goes where it should), the futures-specific ranges the equity side never
sees (negative, zero and zero-crossing quotations), and that the determinism
the helper established survives the new call path.
"""

from __future__ import annotations

import ast
import itertools
from decimal import (
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    Decimal,
    Inexact,
    Rounded,
    getcontext,
    localcontext,
)
from pathlib import Path

import pytest

import northstar_core.strategy as strategy_package
import northstar_core.strategy.futures_asset_analysis_generator as generator_module
from northstar_core.derivatives import ExpirationDate, QuoteValue
from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.value_objects import (
    Currency,
    ExchangeCode,
    PointInTime,
    Price,
    Quantity,
    Symbol,
    Timeframe,
)
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.strategy import (
    AssetAnalysisGenerator,
    FuturesAssetAnalysis,
    FuturesAssetAnalysisGenerator,
    FuturesMarketObservationContext,
    MarketObservationContext,
)

_BULLISH = "strong bullish"
_BEARISH = "strong bearish"
_NEUTRAL = "neutral trend"

_CME = ExchangeCode("CME")
_ES_DEC = FuturesContract(FuturesProductReference(Symbol("ES"), _CME), ExpirationDate("2026-12-18"))
_DAILY = Timeframe("1d")
_INSTANT = PointInTime("2026-09-15T21:00:00Z")


def _context(
    closes: list[str],
    volumes: list[str] | None = None,
    *,
    latest: str | None = None,
    previous: str | None = None,
    latest_volume: str | None = None,
    contract: FuturesContract = _ES_DEC,
    observed_at: PointInTime = _INSTANT,
) -> FuturesMarketObservationContext:
    """Build a context; latest/previous default to the last two closes."""
    volumes = volumes if volumes is not None else ["1000"] * len(closes)
    latest_value = Decimal(latest if latest is not None else closes[-1])
    every_quote = [Decimal(value) for value in closes] + [latest_value]
    return FuturesMarketObservationContext(
        contract=contract,
        timeframe=_DAILY,
        observed_at=observed_at,
        latest_quote=QuoteValue(latest_value),
        previous_close=QuoteValue(Decimal(previous if previous is not None else closes[-2])),
        latest_volume=Quantity(
            Decimal(latest_volume if latest_volume is not None else volumes[-1])
        ),
        session_high=QuoteValue(max(every_quote)),
        session_low=QuoteValue(min(every_quote)),
        recent_closes=tuple(QuoteValue(Decimal(value)) for value in closes),
        recent_volumes=tuple(Quantity(Decimal(value)) for value in volumes),
    )


def _generate(context: FuturesMarketObservationContext) -> FuturesAssetAnalysis:
    return FuturesAssetAnalysisGenerator().generate(context)


def _signal(context: FuturesMarketObservationContext) -> str:
    (signal,) = _generate(context).summarized_signals
    return signal


def _shift(values: list[str], offset: str) -> list[str]:
    return [str(Decimal(value) + Decimal(offset)) for value in values]


_RISING = ["100"] * 15 + ["130"] * 5
_FALLING = ["130"] * 15 + ["100"] * 5
_FLAT = ["110"] * 20

# The 9.7c0 flip case: ambient precision 6 used to read this as no trend.
_FLIP = ["7663.00"] * 19 + ["7663.01"]


# ---------------------------------------------------------------------------
# Signal and construction
# ---------------------------------------------------------------------------


def test_a_rising_confirmed_trend_is_one_strong_bullish_signal() -> None:
    analysis = _generate(_context(_RISING, previous="120"))

    assert analysis.summarized_signals == (_BULLISH,)


def test_a_falling_confirmed_trend_is_one_strong_bearish_signal() -> None:
    analysis = _generate(_context(_FALLING, previous="110"))

    assert analysis.summarized_signals == (_BEARISH,)


def test_an_unconfirmed_series_is_one_neutral_trend_signal() -> None:
    analysis = _generate(_context(_FLAT))

    assert analysis.summarized_signals == (_NEUTRAL,)


def test_volume_below_its_average_withholds_confirmation() -> None:
    assert _signal(_context(_RISING, previous="120", latest_volume="999")) == _NEUTRAL
    assert _signal(_context(_RISING, previous="120", latest_volume="1000")) == _BULLISH


def test_the_generator_reads_latest_quote_and_volume_not_the_series_tail() -> None:
    """Each context field is its own fact; the series tail may differ from it."""
    # recent_closes ends at 130, but the latest quote is 125 and still above 120.
    assert _signal(_context(_RISING, latest="125", previous="120")) == _BULLISH
    # A latest quote below the previous close is falling whatever the tail says.
    assert _signal(_context(_RISING, latest="119", previous="120")) == _NEUTRAL
    # The series tail volume is 1000, but the latest volume is not confirming.
    assert _signal(_context(_RISING, previous="120", latest_volume="1")) == _NEUTRAL


def test_the_analysis_is_a_futures_analysis_of_exactly_the_context_subject() -> None:
    context = _context(_RISING, previous="120")

    analysis = _generate(context)

    assert type(analysis) is FuturesAssetAnalysis
    assert analysis.contract == context.contract
    assert analysis.contract is context.contract
    assert analysis.point_in_time == context.observed_at
    assert analysis.point_in_time is context.observed_at


def test_a_rebuilt_equal_contract_is_carried_by_value() -> None:
    rebuilt = FuturesContract(
        FuturesProductReference(Symbol("ES"), ExchangeCode("CME")), ExpirationDate("2026-12-18")
    )
    assert rebuilt is not _ES_DEC

    analysis = _generate(_context(_RISING, previous="120", contract=rebuilt))

    assert analysis.contract == _ES_DEC


def test_the_analysis_carries_no_price_currency_or_execution_fact() -> None:
    analysis = _generate(_context(_RISING, previous="120"))

    assert set(FuturesAssetAnalysis.__slots__) == {
        "contract",
        "point_in_time",
        "summarized_signals",
    }
    for absent in ("price", "currency", "quote", "quantity", "side", "order", "multiplier"):
        assert not hasattr(analysis, absent)


@pytest.mark.parametrize("value", [None, "context", object()])
def test_a_foreign_context_is_rejected(value: object) -> None:
    with pytest.raises(TypeError, match="FuturesAssetAnalysisGenerator context"):
        FuturesAssetAnalysisGenerator().generate(value)  # type: ignore[arg-type]


def test_an_equity_context_is_rejected() -> None:
    usd = Currency("USD")
    equity = MarketObservationContext(
        listing_reference=ListingReference(Symbol("ES"), ExchangeCode("NASDAQ")),
        observed_at=_INSTANT,
        latest_price=Price("130", usd),
        previous_close=Price("120", usd),
        latest_volume=Quantity("1000"),
        daily_high=Price("130", usd),
        daily_low=Price("100", usd),
        recent_closes=tuple(Price(value, usd) for value in _RISING),
        recent_volumes=tuple(Quantity("1000") for _ in _RISING),
    )

    with pytest.raises(TypeError, match="FuturesMarketObservationContext"):
        FuturesAssetAnalysisGenerator().generate(equity)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Negative, zero and high-precision quotations
# ---------------------------------------------------------------------------

_ASCENDING = [str(7600 + index) for index in range(20)]
_DESCENDING = [str(7600 - index) for index in range(20)]


@pytest.mark.parametrize(
    ("series", "expected"),
    [
        pytest.param(_ASCENDING, _BULLISH, id="positive-rising"),
        pytest.param(_shift(_ASCENDING, "-10000"), _BULLISH, id="all-negative-rising"),
        pytest.param(_shift(_ASCENDING, "-7610"), _BULLISH, id="crossing-zero-rising"),
        pytest.param(_shift(_ASCENDING, "-7619"), _BULLISH, id="rising-to-exactly-zero"),
        pytest.param(_DESCENDING, _BEARISH, id="positive-falling"),
        pytest.param(_shift(_DESCENDING, "-10000"), _BEARISH, id="all-negative-falling"),
        pytest.param(_shift(_DESCENDING, "-7590"), _BEARISH, id="crossing-zero-falling"),
        pytest.param(_shift(_DESCENDING, "-7581"), _BEARISH, id="falling-to-exactly-zero"),
        pytest.param(["-37.63"] * 20, _NEUTRAL, id="flat-negative"),
        pytest.param(["0"] * 20, _NEUTRAL, id="flat-zero"),
    ],
)
def test_the_sign_of_a_quotation_does_not_change_its_reading(
    series: list[str], expected: str
) -> None:
    assert _signal(_context(series)) == expected


def test_a_latest_quote_of_zero_is_an_ordinary_value() -> None:
    series = _shift(_ASCENDING, "-7619")
    context = _context(series)
    assert context.latest_quote.value == 0

    assert _signal(context) == _BULLISH


def test_every_shift_of_a_series_reads_the_same() -> None:
    """The signal only compares, so adding a constant to every quote is invisible."""
    wave = [[str(7600 + ((index * step) % 7) - 3) for index in range(20)] for step in range(1, 30)]
    patterns = wave + [list(reversed(pattern)) for pattern in wave] + [_ASCENDING, _DESCENDING]
    volume_patterns = [["1000"] * 19 + [str(900 + 50 * step)] for step in range(5)]
    offsets = ["-7600", "-7603", "-100000", "0.5", "-7599.999999999"]

    seen = set()
    for pattern, volumes in itertools.product(patterns, volume_patterns):
        base = _signal(_context(pattern, volumes))
        seen.add(base)
        for offset in offsets:
            assert _signal(_context(_shift(pattern, offset), volumes)) == base

    assert seen == {_BULLISH, _BEARISH, _NEUTRAL}


@pytest.mark.parametrize("precision", [6, 28, 50])
def test_nanosecond_quote_increments_are_read_at_every_precision(precision: int) -> None:
    """Databento's 1e-9 fixed point: the last close is one billionth higher."""
    series = ["65.123456789"] * 19 + ["65.123456790"]

    with localcontext() as caller:
        caller.prec = precision
        assert _signal(_context(series)) == _BULLISH


def test_high_precision_negative_quotes_are_read_exactly() -> None:
    series = ["-37.630000001"] * 19 + ["-37.630000000"]

    assert _signal(_context(series)) == _BULLISH
    assert _signal(_context(list(reversed(series)))) == _NEUTRAL


# ---------------------------------------------------------------------------
# Decimal determinism
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("precision", [6, 28, 50])
def test_the_flip_case_is_strong_bullish_at_every_caller_precision(precision: int) -> None:
    context = _context(_FLIP)

    with localcontext() as caller:
        caller.prec = precision
        analysis = _generate(context)

    assert analysis.summarized_signals == (_BULLISH,)


@pytest.mark.parametrize(
    "rounding", [ROUND_DOWN, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, ROUND_HALF_EVEN]
)
@pytest.mark.parametrize("precision", [6, 28, 50])
def test_caller_precision_and_rounding_do_not_reach_the_analysis(
    precision: int, rounding: str
) -> None:
    contexts = [
        _context(_FLIP),
        _context(_shift(_FLIP, "-7663.005")),
        _context(_FALLING, previous="110"),
        _context(_FLAT),
    ]
    expected = [_generate(context) for context in contexts]

    with localcontext() as caller:
        caller.prec = precision
        caller.rounding = rounding
        produced = [_generate(context) for context in contexts]

    assert produced == expected


def test_caller_context_and_flags_are_left_untouched() -> None:
    """Thirty-digit quotes force rounding inside the signal's own context."""
    series = ["1.00000000000000000000000000001"] * 19 + ["1.00000000000000000000000000002"]
    context = _context(series)

    with localcontext() as caller:
        caller.prec = 6
        caller.rounding = ROUND_DOWN
        caller.traps[Rounded] = True
        caller.traps[Inexact] = True
        caller.clear_flags()

        _generate(context)

        assert getcontext().prec == 6
        assert getcontext().rounding == ROUND_DOWN
        assert not caller.flags[Inexact]
        assert not caller.flags[Rounded]


def test_repeated_generation_is_identical() -> None:
    context = _context(_FLIP)
    first = _generate(context)

    assert all(_generate(context) == first for _ in range(25))
    assert repr(_generate(context)) == repr(first)


# ---------------------------------------------------------------------------
# Agreement with the equity generator
# ---------------------------------------------------------------------------


def _equity_context(
    closes: list[str], volumes: list[str], latest: str, previous: str, latest_volume: str
) -> MarketObservationContext:
    usd = Currency("USD")
    return MarketObservationContext(
        listing_reference=ListingReference(Symbol("ES"), ExchangeCode("NASDAQ")),
        observed_at=_INSTANT,
        latest_price=Price(latest, usd),
        previous_close=Price(previous, usd),
        latest_volume=Quantity(latest_volume),
        daily_high=Price("999999", usd),
        daily_low=Price("0", usd),
        recent_closes=tuple(Price(value, usd) for value in closes),
        recent_volumes=tuple(Quantity(value) for value in volumes),
    )


def test_numerically_equal_series_read_the_same_in_both_asset_classes() -> None:
    """Where the two overlap -- non-negative numbers -- they must agree exactly."""
    patterns = [
        _RISING,
        _FALLING,
        _FLAT,
        _FLIP,
        ["7663.01"] * 19 + ["7663.00"],
        ["65.123456789"] * 19 + ["65.123456790"],
        *(
            [str(7600 + ((index * step) % 11) - 5) for index in range(length)]
            for step in range(1, 12)
            for length in (20, 24)
        ),
    ]
    volume_patterns = [["1000"] * 20, ["1082662"] * 19 + ["1082661"], ["500"] * 10 + ["1500"] * 10]

    seen = set()
    for closes, volumes in itertools.product(patterns, volume_patterns):
        volumes = ["1000"] * (len(closes) - len(volumes)) + volumes
        for latest, previous in ((closes[-1], closes[-2]), (closes[-2], closes[-1])):
            futures = _context(closes, volumes, latest=latest, previous=previous)
            equity = _equity_context(closes, volumes, latest, previous, volumes[-1])

            futures_signals = _generate(futures).summarized_signals
            equity_signals = AssetAnalysisGenerator().generate(equity).summarized_signals

            assert futures_signals == equity_signals
            seen.update(futures_signals)

    assert seen == {_BULLISH, _BEARISH, _NEUTRAL}


# ---------------------------------------------------------------------------
# Boundaries and exports
# ---------------------------------------------------------------------------


def _imported_modules() -> set[str]:
    tree = ast.parse(Path(generator_module.__file__).read_text(encoding="utf-8"))
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }


def test_the_generator_depends_only_on_its_context_analysis_and_the_shared_signal() -> None:
    assert _imported_modules() == {
        "__future__",
        "northstar_core.strategy._directional_signal",
        "northstar_core.strategy.value_objects.futures_asset_analysis",
        "northstar_core.strategy.value_objects.futures_market_observation_context",
    }


def test_the_generator_does_no_arithmetic_and_sets_no_decimal_context() -> None:
    tree = ast.parse(Path(generator_module.__file__).read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        assert not isinstance(node, ast.BinOp)
        assert not (isinstance(node, ast.Constant) and isinstance(node.value, float))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"sum", "float", "localcontext", "Decimal"}
    assert "decimal" not in _imported_modules()


def test_the_generator_is_exported_and_the_helper_is_not() -> None:
    assert "FuturesAssetAnalysisGenerator" in strategy_package.__all__
    assert strategy_package.FuturesAssetAnalysisGenerator is (
        generator_module.FuturesAssetAnalysisGenerator
    )
    assert "select_directional_signal" not in strategy_package.__all__
    assert not hasattr(strategy_package, "select_directional_signal")
