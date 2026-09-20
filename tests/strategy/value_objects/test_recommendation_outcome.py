"""Contract test suite for the RecommendationOutcome value object."""

from decimal import ROUND_DOWN, Decimal, getcontext, localcontext

import pytest

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
from northstar_core.strategy import (
    AssetAnalysis,
    InvalidRecommendationOutcomeError,
    Recommendation,
    RecommendationAction,
    RecommendationOutcome,
    ResearchHorizon,
    StrategyIdentity,
)

_USD = Currency("USD")
_EUR = Currency("EUR")
_DECISION_INSTANT = PointInTime("2026-01-20T16:00:00Z")
_EVALUATION_INSTANT = PointInTime("2026-01-21T16:00:00Z")
_UNSET = object()


def _recommendation(
    action: str = "BUY",
    *,
    symbol: str = "AAPL",
    strategy: str = "mvp",
    point_in_time: PointInTime = _DECISION_INSTANT,
) -> Recommendation:
    analysis = AssetAnalysis(
        ListingReference(Symbol(symbol), ExchangeCode("NASDAQ")),
        point_in_time,
        ("strong bullish",),
    )
    return Recommendation(
        action=RecommendationAction(action),
        asset_analysis=analysis,
        strategy_identity=StrategyIdentity(strategy),
        point_in_time=point_in_time,
    )


def _outcome(
    recommendation: object = _UNSET,
    *,
    horizon: object = _UNSET,
    decision_price: object = _UNSET,
    evaluation_instant: object = _UNSET,
    evaluation_price: object = _UNSET,
) -> RecommendationOutcome:
    return RecommendationOutcome(
        _recommendation() if recommendation is _UNSET else recommendation,
        ResearchHorizon(1) if horizon is _UNSET else horizon,
        Price("100", _USD) if decision_price is _UNSET else decision_price,
        _EVALUATION_INSTANT if evaluation_instant is _UNSET else evaluation_instant,
        Price("105", _USD) if evaluation_price is _UNSET else evaluation_price,
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_outcome_from_recommendation_and_market_facts() -> None:
    recommendation = _recommendation()
    outcome = _outcome(recommendation)

    assert outcome.recommendation is recommendation
    assert outcome.horizon == ResearchHorizon(1)
    assert outcome.decision_price == Price("100", _USD)
    assert outcome.evaluation_instant == _EVALUATION_INSTANT
    assert outcome.evaluation_price == Price("105", _USD)


def test_supports_keyword_construction() -> None:
    outcome = RecommendationOutcome(
        recommendation=_recommendation(),
        horizon=ResearchHorizon(20),
        decision_price=Price("100", _USD),
        evaluation_instant=_EVALUATION_INSTANT,
        evaluation_price=Price("110", _USD),
    )

    assert outcome.horizon == ResearchHorizon(20)


def test_decision_instant_is_owned_by_the_recommendation() -> None:
    outcome = _outcome()

    assert outcome.decision_instant == _DECISION_INSTANT
    assert outcome.decision_instant is outcome.recommendation.point_in_time


def test_outcome_does_not_store_a_separate_decision_instant_field() -> None:
    assert "decision_instant" not in RecommendationOutcome.__slots__
    assert not hasattr(_outcome(), "__dict__")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none_recommendation() -> None:
    with pytest.raises(InvalidRecommendationOutcomeError, match="recommendation cannot be None"):
        _outcome(None)


def test_rejects_wrong_recommendation_type() -> None:
    with pytest.raises(InvalidRecommendationOutcomeError, match="must be a Recommendation"):
        _outcome("BUY")


def test_rejects_none_horizon() -> None:
    with pytest.raises(InvalidRecommendationOutcomeError, match="horizon cannot be None"):
        _outcome(horizon=None)


@pytest.mark.parametrize("horizon", [1, "1", Decimal("1")])
def test_rejects_wrong_horizon_type(horizon: object) -> None:
    with pytest.raises(InvalidRecommendationOutcomeError, match="must be a ResearchHorizon"):
        _outcome(horizon=horizon)


def test_rejects_none_decision_price() -> None:
    with pytest.raises(InvalidRecommendationOutcomeError, match="decision price cannot be None"):
        _outcome(decision_price=None)


def test_rejects_none_evaluation_price() -> None:
    with pytest.raises(InvalidRecommendationOutcomeError, match="evaluation price cannot be None"):
        _outcome(evaluation_price=None)


@pytest.mark.parametrize("price", ["100", Decimal("100"), 100])
def test_rejects_wrong_decision_price_type(price: object) -> None:
    with pytest.raises(InvalidRecommendationOutcomeError, match="decision price must be a Price"):
        _outcome(decision_price=price)


def test_rejects_wrong_evaluation_price_type() -> None:
    with pytest.raises(InvalidRecommendationOutcomeError, match="evaluation price must be a Price"):
        _outcome(evaluation_price="105")


def test_rejects_none_evaluation_instant() -> None:
    with pytest.raises(
        InvalidRecommendationOutcomeError, match="evaluation instant cannot be None"
    ):
        _outcome(evaluation_instant=None)


def test_rejects_wrong_evaluation_instant_type() -> None:
    with pytest.raises(
        InvalidRecommendationOutcomeError, match="evaluation instant must be a PointInTime"
    ):
        _outcome(evaluation_instant="2026-01-21T16:00:00Z")


def test_invalid_recommendation_outcome_error_is_a_validation_error() -> None:
    with pytest.raises(ValidationError):
        _outcome(None)


def test_invalid_recommendation_outcome_error_is_a_value_error() -> None:
    with pytest.raises(ValueError):
        _outcome(None)


# ---------------------------------------------------------------------------
# Evaluation instant must be strictly after the decision instant
# ---------------------------------------------------------------------------


def test_rejects_evaluation_instant_equal_to_the_decision_instant() -> None:
    with pytest.raises(InvalidRecommendationOutcomeError, match="strictly after"):
        _outcome(evaluation_instant=_DECISION_INSTANT)


def test_rejects_evaluation_instant_before_the_decision_instant() -> None:
    with pytest.raises(InvalidRecommendationOutcomeError, match="strictly after"):
        _outcome(evaluation_instant=PointInTime("2026-01-19T16:00:00Z"))


def test_accepts_evaluation_instant_strictly_after_the_decision_instant() -> None:
    outcome = _outcome(evaluation_instant=PointInTime("2026-01-20T16:00:01Z"))

    assert outcome.evaluation_instant.compare(outcome.decision_instant) > 0


def test_equality_of_instants_is_compared_semantically_not_textually() -> None:
    recommendation = _recommendation(point_in_time=PointInTime("2026-01-20T16:00:00Z"))

    with pytest.raises(InvalidRecommendationOutcomeError, match="strictly after"):
        _outcome(recommendation, evaluation_instant=PointInTime("2026-01-20T21:30:00+05:30"))


# ---------------------------------------------------------------------------
# Currency invariant
# ---------------------------------------------------------------------------


def test_rejects_currency_mismatch_between_decision_and_evaluation_prices() -> None:
    with pytest.raises(InvalidRecommendationOutcomeError, match="currency must match"):
        _outcome(evaluation_price=Price("105", _EUR))


def test_accepts_consistent_non_usd_currency() -> None:
    outcome = _outcome(
        decision_price=Price("100", _EUR),
        evaluation_price=Price("105", _EUR),
    )

    assert outcome.forward_return == Percentage(5)


# ---------------------------------------------------------------------------
# Zero decision price
# ---------------------------------------------------------------------------


def test_rejects_zero_decision_price() -> None:
    with pytest.raises(InvalidRecommendationOutcomeError, match="decision price cannot be zero"):
        _outcome(decision_price=Price("0", _USD))


def test_accepts_zero_evaluation_price() -> None:
    outcome = _outcome(evaluation_price=Price("0", _USD))

    assert outcome.forward_return == Percentage(-100)


# ---------------------------------------------------------------------------
# Forward return semantics
# ---------------------------------------------------------------------------


def test_positive_forward_return_for_a_rising_market() -> None:
    outcome = _outcome(decision_price=Price("100", _USD), evaluation_price=Price("105", _USD))

    assert outcome.forward_return == Percentage(5)


def test_negative_forward_return_for_a_falling_market() -> None:
    outcome = _outcome(decision_price=Price("100", _USD), evaluation_price=Price("95", _USD))

    assert outcome.forward_return == Percentage(-5)


def test_zero_forward_return_for_an_unchanged_market() -> None:
    outcome = _outcome(decision_price=Price("100", _USD), evaluation_price=Price("100", _USD))

    assert outcome.forward_return == Percentage(0)


def test_forward_return_is_a_percentage_value() -> None:
    assert isinstance(_outcome().forward_return, Percentage)


def test_forward_return_percentage_is_percent_not_ratio() -> None:
    outcome = _outcome(decision_price=Price("100", _USD), evaluation_price=Price("105", _USD))

    assert outcome.forward_return.value == Decimal("5")
    assert outcome.forward_return.value != Decimal("0.05")


def test_forward_return_is_derived_and_not_stored() -> None:
    assert "forward_return" not in RecommendationOutcome.__slots__


def test_forward_return_is_deterministic_across_repeated_reads() -> None:
    outcome = _outcome()

    assert outcome.forward_return == outcome.forward_return


# ---------------------------------------------------------------------------
# Decimal precision and no float usage
# ---------------------------------------------------------------------------


def test_forward_return_preserves_decimal_precision() -> None:
    outcome = _outcome(
        decision_price=Price("100.10", _USD),
        evaluation_price=Price("100.35", _USD),
    )

    expected = (Decimal("100.35") - Decimal("100.10")) / Decimal("100.10") * Decimal(100)
    assert outcome.forward_return == Percentage(expected)


def test_forward_return_value_is_a_decimal_and_never_a_float() -> None:
    forward_return = _outcome(
        decision_price=Price("3", _USD),
        evaluation_price=Price("1", _USD),
    ).forward_return

    assert isinstance(forward_return.value, Decimal)
    assert not isinstance(forward_return.value, float)


def test_recurring_decimal_return_does_not_lose_exactness_to_float() -> None:
    outcome = _outcome(decision_price=Price("3", _USD), evaluation_price=Price("4", _USD))

    expected = (Decimal("4") - Decimal("3")) / Decimal("3") * Decimal(100)
    assert outcome.forward_return.value == Percentage(expected).value


def test_prices_retain_decimal_amounts() -> None:
    outcome = _outcome()

    assert isinstance(outcome.decision_price.amount, Decimal)
    assert isinstance(outcome.evaluation_price.amount, Decimal)


# ---------------------------------------------------------------------------
# Deterministic precision, independent of the ambient Decimal context
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("precision", [6, 28, 50])
def test_forward_return_is_identical_under_any_ambient_precision(precision: int) -> None:
    outcome = _outcome(decision_price=Price("3", _USD), evaluation_price=Price("4", _USD))
    expected = Percentage(Decimal("33.33333333333333333333333333"))

    with localcontext() as context:
        context.prec = precision

        assert outcome.forward_return == expected


def test_forward_return_agrees_across_every_ambient_precision() -> None:
    outcome = _outcome(
        decision_price=Price("100.10", _USD),
        evaluation_price=Price("100.35", _USD),
    )

    returns = []
    for precision in (6, 28, 50):
        with localcontext() as context:
            context.prec = precision
            returns.append(outcome.forward_return)

    assert returns[0] == returns[1] == returns[2] == outcome.forward_return


@pytest.mark.parametrize("precision", [6, 28, 50])
def test_terminating_returns_are_unaffected_by_ambient_precision(precision: int) -> None:
    outcome = _outcome(decision_price=Price("100", _USD), evaluation_price=Price("105", _USD))

    with localcontext() as context:
        context.prec = precision

        assert outcome.forward_return == Percentage(5)


def test_forward_return_does_not_modify_the_caller_decimal_context() -> None:
    outcome = _outcome(decision_price=Price("3", _USD), evaluation_price=Price("4", _USD))
    caller_context = getcontext()
    precision_before = caller_context.prec
    rounding_before = caller_context.rounding

    measured = outcome.forward_return

    assert measured == Percentage(Decimal("33.33333333333333333333333333"))
    assert getcontext() is caller_context
    assert getcontext().prec == precision_before
    assert getcontext().rounding == rounding_before


def test_forward_return_restores_a_customised_caller_context() -> None:
    outcome = _outcome(decision_price=Price("3", _USD), evaluation_price=Price("4", _USD))
    expected = Percentage(Decimal("33.33333333333333333333333333"))

    with localcontext() as context:
        context.prec = 6
        context.rounding = ROUND_DOWN

        measured = outcome.forward_return

        assert measured == expected
        assert getcontext().prec == 6
        assert getcontext().rounding == ROUND_DOWN


# ---------------------------------------------------------------------------
# Purely factual: no action interpretation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("action", ["BUY", "SELL", "HOLD"])
def test_forward_return_is_identical_for_every_recommendation_action(action: str) -> None:
    outcome = _outcome(_recommendation(action))

    assert outcome.forward_return == Percentage(5)


@pytest.mark.parametrize("action", ["BUY", "SELL", "HOLD"])
def test_falling_market_return_is_negative_for_every_action(action: str) -> None:
    outcome = _outcome(_recommendation(action), evaluation_price=Price("95", _USD))

    assert outcome.forward_return == Percentage(-5)


def test_sell_recommendation_return_is_not_sign_inverted() -> None:
    buy = _outcome(_recommendation("BUY"))
    sell = _outcome(_recommendation("SELL"))

    assert buy.forward_return == sell.forward_return == Percentage(5)


def test_outcome_exposes_no_action_interpretation_or_trading_semantics() -> None:
    outcome = _outcome()

    for forbidden in (
        "is_correct",
        "is_successful",
        "aligned_return",
        "profit",
        "pnl",
        "realized_pnl",
        "unrealized_pnl",
        "position",
        "quantity",
        "side",
        "exposure",
        "fill",
        "order",
        "trade",
        "commission",
        "slippage",
        "price_change",
    ):
        assert not hasattr(outcome, forbidden)


def test_outcome_preserves_the_recommendation_action_without_using_it() -> None:
    outcome = _outcome(_recommendation("SELL"))

    assert outcome.recommendation.action == RecommendationAction("SELL")
    assert outcome.forward_return == Percentage(5)


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_outcome_is_immutable() -> None:
    outcome = _outcome()

    with pytest.raises(AttributeError):
        outcome.decision_price = Price("1", _USD)


def test_equal_outcomes_compare_equal_and_hash_equal() -> None:
    left = _outcome(_recommendation())
    right = _outcome(_recommendation())

    assert left == right
    assert hash(left) == hash(right)


def test_outcomes_with_different_horizons_do_not_compare_equal() -> None:
    assert _outcome(horizon=ResearchHorizon(1)) != _outcome(horizon=ResearchHorizon(20))


def test_outcomes_with_different_evaluation_prices_do_not_compare_equal() -> None:
    assert _outcome() != _outcome(evaluation_price=Price("110", _USD))


def test_outcomes_for_different_strategies_do_not_compare_equal() -> None:
    left = _outcome(_recommendation(strategy="mvp"))
    right = _outcome(_recommendation(strategy="momentum"))

    assert left != right


def test_outcomes_for_different_listings_do_not_compare_equal() -> None:
    left = _outcome(_recommendation(symbol="AAPL"))
    right = _outcome(_recommendation(symbol="MSFT"))

    assert left != right


def test_outcome_is_usable_in_sets() -> None:
    outcomes = {_outcome(_recommendation()), _outcome(_recommendation())}

    assert len(outcomes) == 1


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_renders_listing_decision_instant_horizon_and_return() -> None:
    rendered = str(_outcome())

    assert "AAPL@NASDAQ" in rendered
    assert "2026-01-20T16:00:00Z" in rendered
    assert "+1" in rendered
    assert "5%" in rendered


def test_repr_contains_every_recorded_field() -> None:
    representation = repr(_outcome())

    assert "RecommendationOutcome" in representation
    assert "recommendation=" in representation
    assert "horizon=" in representation
    assert "decision_price=" in representation
    assert "evaluation_instant=" in representation
    assert "evaluation_price=" in representation
