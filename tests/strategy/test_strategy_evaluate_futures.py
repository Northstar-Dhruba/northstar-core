"""Tests for Strategy.evaluate_futures.

The futures path must apply the equity decision policy rather than a copy of
it, so beyond pinning BUY/SELL/HOLD these tests run the same signal sets through
both paths and require the same action, including the unknown, mixed and
case-variant sets the policy already handles.
"""

from __future__ import annotations

import ast
import inspect
import textwrap

import pytest

from northstar_core.derivatives import ExpirationDate
from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.value_objects import ExchangeCode, PointInTime, Symbol
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.strategy import (
    AssetAnalysis,
    FuturesAssetAnalysis,
    FuturesRecommendation,
    InvalidStrategyError,
    Recommendation,
    RecommendationAction,
    Strategy,
    StrategyIdentity,
)

_ES_DEC = FuturesContract(
    FuturesProductReference(Symbol("ES"), ExchangeCode("CME")), ExpirationDate("2026-12-18")
)
_INSTANT = PointInTime("2026-09-15T21:00:00Z")
_STRATEGY = Strategy(StrategyIdentity("futures-directional"))


def _analysis(*signals: str, point_in_time: PointInTime = _INSTANT) -> FuturesAssetAnalysis:
    return FuturesAssetAnalysis(
        contract=_ES_DEC, point_in_time=point_in_time, summarized_signals=signals
    )


def _equity_analysis(*signals: str) -> AssetAnalysis:
    return AssetAnalysis(
        listing_reference=ListingReference(Symbol("ES"), ExchangeCode("NASDAQ")),
        point_in_time=_INSTANT,
        summarized_signals=signals,
    )


# ---------------------------------------------------------------------------
# Action mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("signal", "action"),
    [
        ("strong bullish", RecommendationAction("BUY")),
        ("strong bearish", RecommendationAction("SELL")),
        ("neutral trend", RecommendationAction("HOLD")),
    ],
)
def test_each_generated_signal_maps_to_its_directional_view(
    signal: str, action: RecommendationAction
) -> None:
    recommendation = _STRATEGY.evaluate_futures(_analysis(signal))

    assert recommendation.action == action


_SIGNAL_SETS = [
    pytest.param(("strong bullish",), id="bullish"),
    pytest.param(("strong bearish",), id="bearish"),
    pytest.param(("neutral trend",), id="neutral"),
    pytest.param((), id="no-signal"),
    pytest.param(("sideways chop",), id="unknown"),
    pytest.param(("strong bullish", "strong bearish"), id="conflicting"),
    pytest.param(("strong bullish", "neutral trend"), id="bullish-with-neutral"),
    pytest.param(("neutral trend", "strong bearish"), id="bearish-with-neutral"),
    pytest.param(("STRONG BULLISH",), id="upper-case-bullish"),
    pytest.param(("  Strong Bearish  ",), id="padded-mixed-case-bearish"),
    pytest.param(("strong bullish", "strong bullish"), id="repeated-bullish"),
]


@pytest.mark.parametrize("signals", _SIGNAL_SETS)
def test_the_futures_action_is_exactly_the_equity_action_for_every_signal_set(
    signals: tuple[str, ...],
) -> None:
    futures = _STRATEGY.evaluate_futures(_analysis(*signals))
    equity = _STRATEGY.evaluate(_equity_analysis(*signals))

    assert futures.action == equity.action


@pytest.mark.parametrize(
    ("signals", "action"),
    [
        pytest.param(
            ("strong bullish", "strong bearish"), RecommendationAction("HOLD"), id="conflict"
        ),
        pytest.param(("sideways chop",), RecommendationAction("HOLD"), id="unknown"),
        pytest.param((), RecommendationAction("HOLD"), id="empty"),
        pytest.param(("STRONG BULLISH",), RecommendationAction("BUY"), id="case-folded"),
    ],
)
def test_existing_policy_for_unknown_and_mixed_signals_is_inherited(
    signals: tuple[str, ...], action: RecommendationAction
) -> None:
    assert _STRATEGY.evaluate_futures(_analysis(*signals)).action == action


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_the_result_is_a_futures_recommendation_not_an_equity_one() -> None:
    recommendation = _STRATEGY.evaluate_futures(_analysis("strong bullish"))

    assert type(recommendation) is FuturesRecommendation
    assert not isinstance(recommendation, Recommendation)


def test_the_recommendation_is_built_from_exactly_the_analysis_and_strategy() -> None:
    analysis = _analysis("strong bearish")

    recommendation = _STRATEGY.evaluate_futures(analysis)

    assert recommendation.asset_analysis is analysis
    assert recommendation.contract == analysis.contract
    assert recommendation.point_in_time == analysis.point_in_time
    assert recommendation.point_in_time.compare(analysis.point_in_time) == 0
    assert recommendation.strategy_identity == _STRATEGY.strategy_identity


def test_the_decision_instant_follows_the_analysis_instant() -> None:
    later = PointInTime("2026-09-16T21:00:00Z")

    recommendation = _STRATEGY.evaluate_futures(_analysis("neutral trend", point_in_time=later))

    assert recommendation.point_in_time == later


def test_one_strategy_identity_serves_both_asset_classes() -> None:
    futures = _STRATEGY.evaluate_futures(_analysis("strong bullish"))
    equity = _STRATEGY.evaluate(_equity_analysis("strong bullish"))

    assert futures.strategy_identity == equity.strategy_identity == _STRATEGY.strategy_identity


def test_evaluation_is_deterministic() -> None:
    analysis = _analysis("strong bullish")

    assert _STRATEGY.evaluate_futures(analysis) == _STRATEGY.evaluate_futures(analysis)
    assert Strategy(StrategyIdentity("futures-directional")).evaluate_futures(
        analysis
    ) == _STRATEGY.evaluate_futures(analysis)


# ---------------------------------------------------------------------------
# Input validation and separation of the two paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [None, "strong bullish", object()])
def test_a_foreign_value_is_rejected(value: object) -> None:
    with pytest.raises(InvalidStrategyError, match="futures asset analysis"):
        _STRATEGY.evaluate_futures(value)  # type: ignore[arg-type]


def test_an_equity_analysis_is_rejected_by_the_futures_path() -> None:
    with pytest.raises(InvalidStrategyError, match="FuturesAssetAnalysis"):
        _STRATEGY.evaluate_futures(_equity_analysis("strong bullish"))  # type: ignore[arg-type]


def test_a_futures_analysis_is_still_rejected_by_the_equity_path() -> None:
    with pytest.raises(InvalidStrategyError, match="must be an AssetAnalysis"):
        _STRATEGY.evaluate(_analysis("strong bullish"))  # type: ignore[arg-type]


def test_equity_evaluation_still_produces_an_equity_recommendation() -> None:
    recommendation = _STRATEGY.evaluate(_equity_analysis("strong bearish"))

    assert type(recommendation) is Recommendation
    assert recommendation.action == RecommendationAction("SELL")


# ---------------------------------------------------------------------------
# One policy, not two
# ---------------------------------------------------------------------------


def _method_tree(name: str) -> ast.FunctionDef:
    source = textwrap.dedent(inspect.getsource(getattr(Strategy, name)))
    (function,) = ast.parse(source).body
    assert isinstance(function, ast.FunctionDef)
    return function


def test_evaluate_futures_delegates_to_the_shared_action_policy() -> None:
    function = _method_tree("evaluate_futures")

    calls = {
        node.func.attr
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    literals = {
        node.value
        for node in ast.walk(function)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }

    assert "_select_action" in calls
    for vocabulary in ("BUY", "SELL", "HOLD", "strong bullish", "strong bearish"):
        assert vocabulary not in literals


def test_evaluate_futures_documents_that_sell_is_not_an_execution_instruction() -> None:
    documentation = " ".join((Strategy.evaluate_futures.__doc__ or "").split())

    assert "directional research classifications only" in documentation
    for excluded in ("short position", "order side", "margin", "multiplier"):
        assert excluded in documentation
