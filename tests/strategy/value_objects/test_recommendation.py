"""Contract tests for Recommendation identity representation and semantics."""

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.value_objects import ExchangeCode, PointInTime, Symbol
from northstar_core.strategy import (
    AssetAnalysis,
    Recommendation,
    Strategy,
    StrategyIdentity,
)

_INSTANT = PointInTime("2026-09-14T10:00:00Z")


def _recommendation(signal: str = "strong bullish", symbol: str = "AAPL") -> Recommendation:
    analysis = AssetAnalysis(
        ListingReference(Symbol(symbol), ExchangeCode("NASDAQ")),
        _INSTANT,
        (signal,),
    )
    return Strategy(StrategyIdentity("test-strategy")).evaluate(analysis)


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_includes_symbol_resolved_through_listing_reference() -> None:
    recommendation = _recommendation()

    assert str(recommendation) == f"BUY AAPL by test-strategy at {_INSTANT}"


def test_str_reflects_the_listing_reference_symbol() -> None:
    recommendation = _recommendation(symbol="MSFT")

    assert "MSFT" in str(recommendation)


def test_recommendation_reaches_identity_without_a_listing_entity() -> None:
    recommendation = _recommendation()

    assert recommendation.asset_analysis.listing_reference.symbol == Symbol("AAPL")
    assert not hasattr(recommendation.asset_analysis, "listing")


# ---------------------------------------------------------------------------
# Unchanged action semantics
# ---------------------------------------------------------------------------


def test_strong_bullish_signal_still_produces_buy() -> None:
    assert _recommendation("strong bullish").action.value == "BUY"


def test_strong_bearish_signal_still_produces_sell() -> None:
    assert _recommendation("strong bearish").action.value == "SELL"


def test_neutral_signal_still_produces_hold() -> None:
    assert _recommendation("neutral trend").action.value == "HOLD"


def test_recommendation_preserves_analysis_and_point_in_time() -> None:
    recommendation = _recommendation()

    assert recommendation.point_in_time == recommendation.asset_analysis.point_in_time
    assert recommendation.strategy_identity == StrategyIdentity("test-strategy")
