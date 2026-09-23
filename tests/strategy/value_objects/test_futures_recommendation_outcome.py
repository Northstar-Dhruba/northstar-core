"""Tests for FuturesRecommendationOutcome.

The outcome records facts and derives everything else. These tests pin the
three states it can be in, that only the decision quote's sign can make a
return undefined, that the arithmetic is the equity outcome's arithmetic under
the same explicit context, and that BUY, HOLD and SELL never change the answer.
"""

from __future__ import annotations

import ast
import dataclasses
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
from enum import StrEnum
from pathlib import Path

import pytest

import northstar_core.strategy as strategy_package
import northstar_core.strategy.value_objects.futures_recommendation_outcome as outcome_module
from northstar_core.derivatives import ExpirationDate, QuoteValue
from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    Currency,
    ExchangeCode,
    Percentage,
    PointInTime,
    Price,
    Symbol,
)
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.strategy import (
    AssetAnalysis,
    FuturesAssetAnalysis,
    FuturesRecommendation,
    FuturesRecommendationOutcome,
    FuturesRecommendationOutcomeUnavailableReason,
    InvalidFuturesRecommendationOutcomeError,
    RecommendationAction,
    RecommendationOutcome,
    ResearchHorizon,
    Strategy,
    StrategyIdentity,
)

_ES_DEC = FuturesContract(
    FuturesProductReference(Symbol("ES"), ExchangeCode("CME")), ExpirationDate("2026-12-18")
)
_DECISION = PointInTime("2026-09-15T21:00:00Z")
_EVALUATION = PointInTime("2026-09-16T21:00:00Z")
_HORIZON = ResearchHorizon(1)
_STRATEGY = Strategy(StrategyIdentity("futures-directional"))

_INSUFFICIENT = FuturesRecommendationOutcomeUnavailableReason.INSUFFICIENT_FUTURE_OBSERVATIONS
_UNDEFINED = FuturesRecommendationOutcomeUnavailableReason.UNDEFINED_RETURN_BASIS


def _recommendation(signal: str = "neutral trend") -> FuturesRecommendation:
    return _STRATEGY.evaluate_futures(FuturesAssetAnalysis(_ES_DEC, _DECISION, (signal,)))


_BUY = _recommendation("strong bullish")
_SELL = _recommendation("strong bearish")
_HOLD = _recommendation("neutral trend")


def _quote(value: str) -> QuoteValue:
    return QuoteValue(Decimal(value))


def _outcome(
    decision: str,
    evaluation: str | None,
    *,
    recommendation: FuturesRecommendation = _HOLD,
    evaluation_instant: PointInTime = _EVALUATION,
) -> FuturesRecommendationOutcome:
    if evaluation is None:
        return FuturesRecommendationOutcome(recommendation, _HORIZON, _quote(decision))
    return FuturesRecommendationOutcome(
        recommendation, _HORIZON, _quote(decision), evaluation_instant, _quote(evaluation)
    )


# ---------------------------------------------------------------------------
# Measured: a strictly positive decision quote
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("decision", "evaluation", "percent"),
    [
        ("100", "110", "10"),
        ("100", "90", "-10"),
        ("100", "100", "0"),
        ("10", "0", "-100"),
        ("10", "-5", "-150"),
        ("0.5", "-37.63", "-7626"),
        ("65.123456789", "65.123456790", "0.00000000153554502372317243548034288"),
    ],
)
def test_a_positive_decision_quote_measures_a_signed_percentage(
    decision: str, evaluation: str, percent: str
) -> None:
    outcome = _outcome(decision, evaluation)

    assert outcome.forward_return == Percentage(Decimal(percent))
    assert outcome.unavailable_reason is None
    assert outcome.decision_quote == _quote(decision)
    assert outcome.evaluation_quote == _quote(evaluation)
    assert outcome.evaluation_instant == _EVALUATION


def test_a_zero_or_negative_evaluation_quote_is_not_a_reason_to_withhold_a_return() -> None:
    for evaluation in ("0", "-5", "-37.63", "-1000000"):
        assert _outcome("10", evaluation).unavailable_reason is None


# ---------------------------------------------------------------------------
# Undefined return basis: a zero or negative decision quote
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("decision", "evaluation"),
    [
        pytest.param("0", "10", id="zero-to-positive"),
        pytest.param("0", "0", id="zero-to-zero"),
        pytest.param("0", "-10", id="zero-to-negative"),
        pytest.param("-10", "-5", id="negative-rising"),
        pytest.param("-10", "-20", id="negative-falling"),
        pytest.param("-10", "10", id="negative-to-positive"),
        pytest.param("-37.63", "-37.63", id="negative-unchanged"),
        pytest.param("-0.000000001", "5", id="just-below-zero"),
    ],
)
def test_a_non_positive_decision_quote_has_an_undefined_return_basis(
    decision: str, evaluation: str
) -> None:
    outcome = _outcome(decision, evaluation)

    assert outcome.forward_return is None
    assert outcome.unavailable_reason == _UNDEFINED
    # Both factual quotes remain recorded; only the percentage is withheld.
    assert outcome.decision_quote == _quote(decision)
    assert outcome.evaluation_quote == _quote(evaluation)
    assert outcome.evaluation_instant == _EVALUATION


def test_the_smallest_positive_decision_quote_is_measurable() -> None:
    outcome = _outcome("0.000000001", "0.000000002")

    assert outcome.unavailable_reason is None
    assert outcome.forward_return == Percentage(Decimal("100"))


def test_an_undefined_basis_is_never_reported_as_a_zero_movement() -> None:
    outcome = _outcome("0", "0")

    assert outcome.forward_return is None
    assert outcome.forward_return != Percentage(Decimal("0"))


# ---------------------------------------------------------------------------
# Insufficient future observations: the horizon has not been reached
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("decision", ["100", "0", "-10"])
def test_an_outcome_without_an_evaluation_observation_is_insufficient(decision: str) -> None:
    """Insufficiency comes first: the basis question needs an evaluation quote."""
    outcome = _outcome(decision, None)

    assert outcome.unavailable_reason == _INSUFFICIENT
    assert outcome.forward_return is None
    assert outcome.decision_quote == _quote(decision)
    assert outcome.evaluation_quote is None
    assert outcome.evaluation_instant is None


def test_the_two_unavailable_states_are_structurally_distinguishable() -> None:
    insufficient = _outcome("-10", None)
    undefined = _outcome("-10", "-5")

    assert insufficient.unavailable_reason != undefined.unavailable_reason
    assert insufficient.evaluation_quote is None
    assert undefined.evaluation_quote is not None


# ---------------------------------------------------------------------------
# State coherence
# ---------------------------------------------------------------------------


def test_every_reachable_state_has_exactly_one_of_return_and_reason() -> None:
    quotes = ["-10", "-0.5", "0", "0.5", "10", "100"]
    for decision, evaluation in itertools.product(quotes, [*quotes, None]):
        outcome = _outcome(decision, evaluation)

        assert (outcome.forward_return is None) != (outcome.unavailable_reason is None)
        if outcome.forward_return is not None:
            assert outcome.evaluation_quote is not None
            assert outcome.decision_quote.value > 0
        if outcome.unavailable_reason == _UNDEFINED:
            assert outcome.evaluation_quote is not None
            assert outcome.decision_quote.value <= 0
        if outcome.unavailable_reason == _INSUFFICIENT:
            assert outcome.evaluation_quote is None


def test_only_the_facts_are_fields_so_contradictions_cannot_be_expressed() -> None:
    assert [field.name for field in dataclasses.fields(FuturesRecommendationOutcome)] == [
        "recommendation",
        "horizon",
        "decision_quote",
        "evaluation_instant",
        "evaluation_quote",
    ]


@pytest.mark.parametrize(
    "contradiction",
    [
        {"forward_return": Percentage(Decimal("10"))},
        {"unavailable_reason": _UNDEFINED},
        {"unavailable_reason": _INSUFFICIENT, "forward_return": Percentage(Decimal("10"))},
    ],
)
def test_a_return_or_reason_cannot_be_supplied(contradiction: dict[str, object]) -> None:
    with pytest.raises(TypeError):
        FuturesRecommendationOutcome(  # type: ignore[call-arg]
            _HOLD, _HORIZON, _quote("100"), _EVALUATION, _quote("110"), **contradiction
        )


def test_the_derived_views_cannot_be_overwritten() -> None:
    outcome = _outcome("100", "110")

    for name, value in (
        ("forward_return", Percentage(Decimal("0"))),
        ("unavailable_reason", _UNDEFINED),
        ("evaluation_quote", _quote("1")),
    ):
        with pytest.raises(AttributeError):
            setattr(outcome, name, value)


def test_an_evaluation_instant_without_a_quote_is_rejected() -> None:
    with pytest.raises(InvalidFuturesRecommendationOutcomeError, match="both present or both"):
        FuturesRecommendationOutcome(_HOLD, _HORIZON, _quote("100"), _EVALUATION, None)


def test_an_evaluation_quote_without_an_instant_is_rejected() -> None:
    with pytest.raises(InvalidFuturesRecommendationOutcomeError, match="both present or both"):
        FuturesRecommendationOutcome(_HOLD, _HORIZON, _quote("100"), None, _quote("110"))


@pytest.mark.parametrize(
    "instant",
    [
        pytest.param("2026-09-15T21:00:00Z", id="at-the-decision"),
        pytest.param("2026-09-15T16:00:00-05:00", id="offset-spelling-of-the-decision"),
        pytest.param("2026-09-14T21:00:00Z", id="before-the-decision"),
    ],
)
def test_the_evaluation_must_be_strictly_after_the_decision(instant: str) -> None:
    with pytest.raises(InvalidFuturesRecommendationOutcomeError, match="strictly after"):
        _outcome("100", "110", evaluation_instant=PointInTime(instant))


def test_half_a_second_after_the_decision_is_strictly_after() -> None:
    outcome = _outcome("100", "110", evaluation_instant=PointInTime("2026-09-15T21:00:00.5Z"))

    assert outcome.evaluation_instant.compare(outcome.decision_instant) > 0


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


def _equity_recommendation() -> object:
    analysis = AssetAnalysis(ListingReference(Symbol("ES"), ExchangeCode("NASDAQ")), _DECISION, ())
    return _STRATEGY.evaluate(analysis)


@pytest.mark.parametrize("value", [None, "BUY", _equity_recommendation()])
def test_the_recommendation_must_be_a_futures_recommendation(value: object) -> None:
    with pytest.raises(InvalidFuturesRecommendationOutcomeError, match="recommendation"):
        FuturesRecommendationOutcome(value, _HORIZON, _quote("100"))  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [None, 1, "1"])
def test_the_horizon_must_be_a_research_horizon(value: object) -> None:
    with pytest.raises(InvalidFuturesRecommendationOutcomeError, match="horizon"):
        FuturesRecommendationOutcome(_HOLD, value, _quote("100"))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value", [None, Decimal("100"), 100, Price("100", Currency("USD"))], ids=repr
)
def test_the_decision_quote_must_be_a_quote_value(value: object) -> None:
    with pytest.raises(InvalidFuturesRecommendationOutcomeError, match="decision quote"):
        FuturesRecommendationOutcome(_HOLD, _HORIZON, value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [Decimal("110"), Price("110", Currency("USD"))], ids=repr)
def test_the_evaluation_quote_must_be_a_quote_value(value: object) -> None:
    with pytest.raises(InvalidFuturesRecommendationOutcomeError, match="evaluation quote"):
        FuturesRecommendationOutcome(_HOLD, _HORIZON, _quote("100"), _EVALUATION, value)  # type: ignore[arg-type]


def test_the_evaluation_instant_must_be_a_point_in_time() -> None:
    with pytest.raises(InvalidFuturesRecommendationOutcomeError, match="evaluation instant"):
        FuturesRecommendationOutcome(
            _HOLD,
            _HORIZON,
            _quote("100"),
            "2026-09-16T21:00:00Z",
            _quote("110"),  # type: ignore[arg-type]
        )


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesRecommendationOutcomeError, ValidationError)


# ---------------------------------------------------------------------------
# Deterministic arithmetic
# ---------------------------------------------------------------------------

# One third of a percent per point: every one of these repeats forever.
_REPEATING = [("3", "4"), ("7", "9"), ("65.123456789", "65.123456790"), ("0.3", "-0.1")]


def _returns() -> list[Percentage | None]:
    return [_outcome(decision, evaluation).forward_return for decision, evaluation in _REPEATING]


@pytest.mark.parametrize(
    "rounding", [ROUND_DOWN, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, ROUND_HALF_EVEN]
)
@pytest.mark.parametrize("precision", [6, 28, 50])
def test_the_return_is_identical_under_any_caller_context(precision: int, rounding: str) -> None:
    expected = _returns()

    with localcontext() as caller:
        caller.prec = precision
        caller.rounding = rounding
        produced = _returns()

    assert produced == expected


def test_the_return_is_computed_at_twenty_eight_digits_half_even() -> None:
    assert _outcome("3", "4").forward_return == Percentage(Decimal("33.33333333333333333333333333"))
    context = outcome_module._RETURN_CONTEXT
    assert (context.prec, context.rounding) == (28, ROUND_HALF_EVEN)


def test_low_caller_precision_would_have_changed_the_answer() -> None:
    """Guard: the determinism test is load-bearing only if this holds."""
    with localcontext() as caller:
        caller.prec = 6
        ambient = (Decimal("4") - Decimal("3")) / Decimal("3") * Decimal(100)

    assert Percentage(ambient) != _outcome("3", "4").forward_return


def test_the_caller_context_and_flags_are_left_untouched() -> None:
    outcome = _outcome("3", "4")

    with localcontext() as caller:
        caller.prec = 6
        caller.rounding = ROUND_DOWN
        caller.traps[Inexact] = True
        caller.traps[Rounded] = True
        caller.clear_flags()

        outcome.forward_return  # noqa: B018 - the computation is the point

        assert getcontext().prec == 6
        assert getcontext().rounding == ROUND_DOWN
        assert not caller.flags[Inexact]
        assert not caller.flags[Rounded]
    assert not any(outcome_module._RETURN_CONTEXT.flags.values())


def test_repeated_reads_return_one_value() -> None:
    outcome = _outcome("65.123456789", "65.123456790")

    assert len({outcome.forward_return for _ in range(20)}) == 1


def test_a_positive_series_measures_exactly_what_the_equity_outcome_measures() -> None:
    """Where both apply, the futures and equity arithmetic must agree."""
    usd = Currency("USD")
    equity_recommendation = _equity_recommendation()
    quotes = ["0.01", "1", "3", "7", "10", "65.123456789", "99.99", "7663.25", "123456.789"]

    for decision, evaluation in itertools.product(quotes, quotes):
        equity = RecommendationOutcome(
            equity_recommendation,  # type: ignore[arg-type]
            _HORIZON,
            Price(decision, usd),
            _EVALUATION,
            Price(evaluation, usd),
        )
        assert _outcome(decision, evaluation).forward_return == equity.forward_return


# ---------------------------------------------------------------------------
# Action independence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("decision", "evaluation"),
    [("100", "110"), ("100", "90"), ("10", "-5"), ("0", "10"), ("-10", "-5"), ("100", None)],
)
def test_buy_hold_and_sell_describe_the_same_market_movement(
    decision: str, evaluation: str | None
) -> None:
    assert {_BUY.action, _HOLD.action, _SELL.action} == {
        RecommendationAction("BUY"),
        RecommendationAction("HOLD"),
        RecommendationAction("SELL"),
    }

    outcomes = [
        _outcome(decision, evaluation, recommendation=recommendation)
        for recommendation in (_BUY, _HOLD, _SELL)
    ]

    assert len({outcome.forward_return for outcome in outcomes}) == 1
    assert len({outcome.unavailable_reason for outcome in outcomes}) == 1


def test_a_sell_after_a_fall_is_still_a_negative_movement() -> None:
    assert _outcome("100", "90", recommendation=_SELL).forward_return == Percentage(Decimal("-10"))


def test_the_outcome_module_never_reads_the_action() -> None:
    tree = ast.parse(Path(outcome_module.__file__).read_text(encoding="utf-8"))

    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }

    assert "action" not in attributes
    assert "RecommendationAction" not in names
    assert not {"BUY", "SELL", "HOLD"} & literals


def test_the_outcome_carries_no_execution_or_money_concept() -> None:
    outcome = _outcome("100", "110")

    for absent in (
        "pnl",
        "profit",
        "side",
        "position",
        "quantity",
        "multiplier",
        "margin",
        "currency",
        "decision_price",
        "evaluation_price",
    ):
        assert not hasattr(outcome, absent)


def test_the_outcome_imports_no_price_money_or_currency() -> None:
    tree = ast.parse(Path(outcome_module.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }

    assert not {"Price", "Money", "Currency", "ListingReference"} & imported


# ---------------------------------------------------------------------------
# Identity, vocabulary and surface
# ---------------------------------------------------------------------------


def test_the_only_subject_identity_is_the_recommendation_contract() -> None:
    """No second contract field exists, so none can disagree with the first."""
    outcome = _outcome("100", "110")

    assert outcome.recommendation.contract == _ES_DEC
    assert outcome.decision_instant == _DECISION
    for absent in ("contract", "listing_reference", "product", "decision_point_in_time"):
        assert absent not in {field.name for field in dataclasses.fields(outcome)}


def test_the_unavailable_vocabulary_is_exactly_the_two_futures_reasons() -> None:
    assert issubclass(FuturesRecommendationOutcomeUnavailableReason, StrEnum)
    assert [reason.value for reason in FuturesRecommendationOutcomeUnavailableReason] == [
        "INSUFFICIENT_FUTURE_OBSERVATIONS",
        "UNDEFINED_RETURN_BASIS",
    ]
    assert "CURRENCY_MISMATCH" not in FuturesRecommendationOutcomeUnavailableReason.__members__


def test_equal_facts_give_equal_outcomes() -> None:
    assert _outcome("100", "110") == _outcome("100", "110")
    assert _outcome("100", "110") != _outcome("100", "111")
    assert _outcome("100", None) != _outcome("100", "110")


def test_str_and_repr_describe_the_state() -> None:
    assert str(_outcome("100", "110")).endswith("+1 10%")
    assert str(_outcome("0", "110")).endswith("+1 UNDEFINED_RETURN_BASIS")
    assert str(_outcome("100", None)).endswith("+1 INSUFFICIENT_FUTURE_OBSERVATIONS")
    assert repr(_outcome("100", None)).startswith("FuturesRecommendationOutcome(recommendation=")


def test_the_outcome_and_its_reason_are_exported() -> None:
    for name in (
        "FuturesRecommendationOutcome",
        "FuturesRecommendationOutcomeUnavailableReason",
        "InvalidFuturesRecommendationOutcomeError",
    ):
        assert name in strategy_package.__all__
    for private in ("_RETURN_CONTEXT", "_PERCENT_SCALE"):
        assert not hasattr(strategy_package, private)
