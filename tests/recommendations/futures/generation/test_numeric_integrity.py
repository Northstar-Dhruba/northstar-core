"""Regression tests for the F-4 numeric contracts (review findings D-1, D-2, D-3).

D-1  A proposal whose reward or risk cannot be represented exactly raises the
     proposal-domain error, chained from the decimal signal; never a raw one.
D-2  No calculation records a flag on a shared Decimal context, and the caller's
     own context is neither used nor changed.
D-3  Explanations and risk text are fixed-point -- 0.0000001, never 1E-7.

Synthetic data only; the multipliers and increments are non-production fixtures.
"""

from __future__ import annotations

import dataclasses
import decimal
import re
from decimal import Decimal, Inexact, Rounded

import pytest

from northstar_core.derivatives import ExpirationDate, QuoteValue
from northstar_core.foundation.value_objects import (
    ExchangeCode,
    PointInTime,
    Quantity,
    Symbol,
    Timeframe,
)
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.recommendations.futures import (
    EntryZone,
    FuturesCandidateEvidence,
    FuturesCandidateSelection,
    FuturesCandidateSelectionCriteria,
    FuturesRecommendationGeneration,
    FuturesRecommendationGenerationPolicy,
    FuturesRecommendationProposal,
    FuturesRecommendationSessionWindow,
    FuturesResearchDecision,
    FuturesResearchDecisionReference,
    FuturesTradeRecommendationIdentity,
    InvalidFuturesRecommendationGenerationError,
    InvalidFuturesRecommendationProposalError,
    PriceMovementUnit,
    PriceTarget,
    RecommendationPolicyVersion,
    RecommendationValidity,
    RewardToRisk,
    StopLoss,
    TradeDirection,
)
from northstar_core.recommendations.futures.generation import _price_levels
from northstar_core.strategy import (
    ExplanationReason,
    FuturesAssetAnalysis,
    FuturesMarketObservationContext,
    FuturesRecommendation,
    RecommendationAction,
    StrategyIdentity,
)

_NIFTY = FuturesProductReference(Symbol("NIFTY"), ExchangeCode("NSE"))
_OCT = FuturesContract(_NIFTY, ExpirationDate("2026-10-27"))
_DAILY = Timeframe("1d")
_STRATEGY = StrategyIdentity("synthetic-directional-v1")
_SESSION = PointInTime("2026-10-07T10:00:00Z")
_ISSUED = PointInTime("2026-10-07T12:00:00Z")
_ELIGIBLE = PointInTime("2026-10-08T10:00:00Z")
_THROUGH = PointInTime("2026-10-21T10:00:00Z")
_CUTOFF = PointInTime("2026-10-27T10:00:00Z")
_SOURCE = FuturesResearchDecisionReference(_OCT, _DAILY, _SESSION, _STRATEGY)

_RISING = tuple(str(24000 + 20 * step) for step in range(19)) + ("24383",)
_STEADY = tuple(str(24000 + 20 * step) for step in range(20))
_TINY = tuple(str(Decimal("1") + Decimal("0.0000001") * step) for step in range(20))
_TINY_NEGATIVE = tuple(
    str(Decimal("-0.0000020") + Decimal("0.0000001") * step) for step in range(20)
)
_SCIENTIFIC = re.compile(r"\d[eE][+-]?\d")


def _q(value: str) -> QuoteValue:
    return QuoteValue(Decimal(value))


def _policy(**overrides: object) -> FuturesRecommendationGenerationPolicy:
    values: dict[str, object] = {
        "version": RecommendationPolicyVersion("f4-synthetic-fixture-v1"),
        "approved_strategies": (_STRATEGY,),
        "lookback_changes": 19,
        "entry_multiplier": Decimal("0.25"),
        "stop_multiplier": Decimal("1.5"),
        "target_multiplier": Decimal("3"),
        "price_increment": Decimal("0.05"),
        "min_reward_to_risk": Decimal("1.5"),
        "short_enabled": True,
    }
    values.update(overrides)
    return FuturesRecommendationGenerationPolicy(**values)  # type: ignore[arg-type]


def _generate(
    closes: tuple[str, ...] = _RISING,
    *,
    action: str = "BUY",
    policy: FuturesRecommendationGenerationPolicy | None = None,
) -> FuturesRecommendationGeneration:
    decision = FuturesResearchDecision(
        _SOURCE,
        FuturesRecommendation(
            action=RecommendationAction(action),
            asset_analysis=FuturesAssetAnalysis(_OCT, _SESSION, ("synthetic",)),
            strategy_identity=_STRATEGY,
            point_in_time=_SESSION,
        ),
    )
    quotes = tuple(_q(close) for close in closes)
    context = FuturesMarketObservationContext(
        contract=_OCT,
        timeframe=_DAILY,
        observed_at=_SESSION,
        latest_quote=quotes[-1],
        previous_close=quotes[-2],
        latest_volume=Quantity(Decimal("1000")),
        session_high=quotes[-1],
        session_low=quotes[-1],
        recent_closes=quotes,
        recent_volumes=tuple(Quantity(Decimal("1000")) for _ in quotes),
    )
    selection = FuturesCandidateSelection.select(
        FuturesCandidateSelectionCriteria(_SESSION, (_NIFTY,), (_STRATEGY,)), (decision,)
    )
    return FuturesRecommendationGeneration.generate(
        policy or _policy(),
        selection,
        (FuturesCandidateEvidence(_SOURCE, context),),
        (FuturesRecommendationSessionWindow(_OCT, _ELIGIBLE, _THROUGH, _CUTOFF),),
        (),
        _ISSUED,
    )


def _proposal(
    low: str = "100", high: str = "101", stop: str = "98", target: str = "105", **overrides: object
) -> FuturesRecommendationProposal:
    fields: dict[str, object] = {
        "contract": _OCT,
        "direction": TradeDirection.LONG,
        "entry": EntryZone(_q(low), _q(high)),
        "stop": StopLoss(_q(stop)),
        "target": PriceTarget(_q(target)),
        "validity": RecommendationValidity(_ELIGIBLE, _THROUGH, _CUTOFF),
        "source": _SOURCE,
        "policy_version": RecommendationPolicyVersion("f4-synthetic-fixture-v1"),
        "issued_at": _ISSUED,
        "thesis": (ExplanationReason("Synthetic thesis"),),
        "reference_price": _q("100"),
        "movement_unit": PriceMovementUnit(Decimal("1"), 19),
        "reward_to_risk": RewardToRisk(Decimal("4"), Decimal("3")),
    }
    fields.update(overrides)
    return FuturesRecommendationProposal(**fields)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# D-1 -- proposal-domain error for unrepresentable reward or risk
# ---------------------------------------------------------------------------


def test_the_reviewed_high_precision_entry_raises_the_proposal_error() -> None:
    """Reward 105 - 101.0000000000000000000000000001 needs 31 significant digits."""
    with pytest.raises(InvalidFuturesRecommendationProposalError) as raised:
        _proposal(high="101.0000000000000000000000000001")

    assert type(raised.value) is InvalidFuturesRecommendationProposalError
    assert isinstance(raised.value.__cause__, Inexact | Rounded)


@pytest.mark.parametrize(
    "levels",
    [
        {"stop": "-0.0000000000000000000000000001"},
        {"target": "100000000000000000000000000000.5"},
    ],
    ids=["risk-beyond-precision", "reward-beyond-precision"],
)
def test_risk_or_reward_beyond_precision_raises_the_proposal_error(
    levels: dict[str, str],
) -> None:
    with pytest.raises(InvalidFuturesRecommendationProposalError) as raised:
        _proposal(**levels)  # type: ignore[arg-type]

    assert isinstance(raised.value.__cause__, Inexact | Rounded)


def test_an_unrelated_proposal_error_is_not_reported_as_a_precision_failure() -> None:
    with pytest.raises(InvalidFuturesRecommendationProposalError, match="opposite sides") as raised:
        _proposal(stop="100")

    assert raised.value.__cause__ is None


def test_a_wrong_type_is_still_a_type_error_of_the_proposal() -> None:
    with pytest.raises(InvalidFuturesRecommendationProposalError, match="must be a"):
        _proposal(entry=None)


def test_high_precision_levels_within_precision_are_accepted_and_rebuilt() -> None:
    """Levels on a 1E-20 grid carry about 25 significant digits: exact, so valid."""
    (proposal,) = _generate(policy=_policy(price_increment=Decimal("1E-20"))).proposals

    rebuilt = FuturesRecommendationProposal(
        **{field.name: getattr(proposal, field.name) for field in dataclasses.fields(proposal)}
    )

    assert rebuilt == proposal
    assert proposal.entry.low == _q("24377.96052631578947368422")
    recommendation = rebuilt.to_recommendation(FuturesTradeRecommendationIdentity("hp-1"))
    assert recommendation.entry == proposal.entry


def test_an_ordinary_proposal_is_unaffected() -> None:
    assert _proposal().reward_to_risk == RewardToRisk(Decimal("4"), Decimal("3"))


# ---------------------------------------------------------------------------
# D-2 -- no shared or caller Decimal context state
# ---------------------------------------------------------------------------


def _no_flags(context: decimal.Context) -> bool:
    return not any(context.flags.values())


def _module_contexts() -> tuple[decimal.Context, decimal.Context]:
    return _price_levels._EXACT_CONTEXT, _price_levels._DISPLAY_CONTEXT


def test_module_contexts_keep_no_flags_after_inexact_display_and_error_paths() -> None:
    _generate()  # U = 383/19 is displayed inexactly
    _generate(action="SELL", closes=tuple(reversed(_RISING)))
    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        _generate(policy=_policy(price_increment=Decimal("1E-27")))  # trapped Inexact
    with pytest.raises(InvalidFuturesRecommendationProposalError):
        _proposal(high="101.0000000000000000000000000001")

    for context in _module_contexts():
        assert _no_flags(context)


def test_module_context_configuration_is_unchanged() -> None:
    _generate()
    exact, display = _module_contexts()

    assert (exact.prec, exact.rounding) == (28, decimal.ROUND_HALF_EVEN)
    assert exact.traps[Inexact] and exact.traps[Rounded]
    assert (display.prec, display.rounding) == (28, decimal.ROUND_HALF_EVEN)
    assert not display.traps[Inexact]


def test_the_callers_context_is_neither_used_nor_changed() -> None:
    with decimal.localcontext() as caller:
        caller.prec = 3
        caller.rounding = decimal.ROUND_DOWN
        caller.traps[Inexact] = True
        caller.traps[Rounded] = True
        caller.clear_flags()

        (proposal,) = _generate().proposals

        assert _no_flags(caller)
        assert (caller.prec, caller.rounding) == (3, decimal.ROUND_DOWN)
    assert proposal == _generate().proposals[0]
    assert proposal.target == PriceTarget(_q("24448.45"))


def test_results_do_not_depend_on_call_order() -> None:
    long_first = (_generate(), _generate(action="SELL", closes=tuple(reversed(_RISING))))
    short_first = (_generate(action="SELL", closes=tuple(reversed(_RISING))), _generate())

    assert long_first == tuple(reversed(short_first))


# ---------------------------------------------------------------------------
# D-3 -- fixed-point explanations and risk text
# ---------------------------------------------------------------------------


def _signals(generation: FuturesRecommendationGeneration) -> tuple[str, ...]:
    (proposal,) = generation.proposals
    return proposal.thesis[1].supporting_signals


def test_the_golden_thesis_marks_a_rounded_movement_unit() -> None:
    assert _signals(_generate()) == (
        "reference close 24383",
        "mean absolute close-to-close change 20.15789473684210526315789474 "
        "(rounded to 28 significant digits) over 19 changes",
        "worst entry 24388",
        "reward 60.45 against risk 40.25",
    )


def test_an_exact_movement_unit_carries_no_rounding_note() -> None:
    assert (
        _signals(_generate(_STEADY))[1] == "mean absolute close-to-close change 20 over 19 changes"
    )


def test_small_units_stops_and_rewards_are_fixed_point() -> None:
    """U = 1E-7 exactly; zone [1.000001875, 1.000001925]; risk 2E-7, reward 3E-7."""
    generation = _generate(_TINY, policy=_policy(price_increment=Decimal("1E-9")))

    assert _signals(generation) == (
        "reference close 1.0000019",
        "mean absolute close-to-close change 0.0000001 over 19 changes",
        "worst entry 1.000001925",
        "reward 0.0000003 against risk 0.0000002",
    )
    (proposal,) = generation.proposals
    assert str(proposal.reward_to_risk) == "0.0000003:0.0000002"
    assert str(proposal.movement_unit) == "0.0000001 over 19 changes"
    assert proposal.reward_to_risk.reward == Decimal("3E-7")


def test_negative_small_quotations_keep_their_sign_in_fixed_point() -> None:
    """Closes -0.0000020 ... -0.0000001; zone [-0.000000125, -0.000000075]."""
    generation = _generate(_TINY_NEGATIVE, policy=_policy(price_increment=Decimal("1E-9")))

    signals = _signals(generation)
    assert signals[0] == "reference close -0.0000001"
    assert signals[2] == "worst entry -0.000000075"
    assert not any(_SCIENTIFIC.search(signal) for signal in signals)


@pytest.mark.parametrize("closes", [_RISING, _STEADY, _TINY, _TINY_NEGATIVE])
def test_no_explanation_or_risk_text_uses_scientific_notation(closes: tuple[str, ...]) -> None:
    """A fine grid rounds the golden setup just below 1.5, so the minimum is 1.4 here."""
    policy = _policy(price_increment=Decimal("1E-9"), min_reward_to_risk=Decimal("1.4"))
    (proposal,) = _generate(closes, policy=policy).proposals

    texts = [reason.rationale for reason in proposal.thesis]
    texts += [signal for reason in proposal.thesis for signal in reason.supporting_signals]
    texts += [str(proposal.reward_to_risk), str(proposal.movement_unit)]
    assert not any(_SCIENTIFIC.search(text) for text in texts)


def test_display_text_is_deterministic() -> None:
    first = _generate(_TINY, policy=_policy(price_increment=Decimal("1E-9")))
    second = _generate(_TINY, policy=_policy(price_increment=Decimal("1E-9")))

    assert _signals(first) == _signals(second)
    assert str(first.proposals[0].reward_to_risk) == str(second.proposals[0].reward_to_risk)


def test_fixed_point_display_keeps_every_digit_and_the_sign() -> None:
    assert str(RewardToRisk(Decimal("1.2E-12"), Decimal("4.50"))) == "0.0000000000012:4.50"
    assert str(PriceMovementUnit(Decimal("1E-10"), 1)) == "0.0000000001 over 1 changes"
    assert _price_levels.fixed_point(Decimal("-1E-7")) == "-0.0000001"


# ---------------------------------------------------------------------------
# J-2 -- fixed-point, unambiguous proposal text
# ---------------------------------------------------------------------------


def test_proposal_text_brackets_negative_tiny_bounds_in_fixed_point() -> None:
    """Zone [-0.000000125, -0.000000075], stop -0.000000275, target 0.000000225."""
    generation = _generate(_TINY_NEGATIVE, policy=_policy(price_increment=Decimal("1E-9")))
    (proposal,) = generation.proposals

    assert str(proposal) == (
        "proposal LONG NIFTY@NSE 2026-10-27 entry [-0.000000125, -0.000000075] "
        "stop -0.000000275 target 0.000000225 reward:risk 0.0000003:0.0000002 "
        "under f4-synthetic-fixture-v1"
    )


def test_proposal_text_for_small_positive_values_is_fixed_point() -> None:
    generation = _generate(_TINY, policy=_policy(price_increment=Decimal("1E-9")))
    (proposal,) = generation.proposals

    assert "entry [1.000001875, 1.000001925] stop 1.000001725 target 1.000002225" in str(proposal)


def test_proposal_text_at_normal_scale_is_unchanged_in_value() -> None:
    (proposal,) = _generate().proposals

    assert str(proposal) == (
        "proposal LONG NIFTY@NSE 2026-10-27 entry [24378, 24388] stop 24347.75 "
        "target 24448.45 reward:risk 60.45:40.25 under f4-synthetic-fixture-v1"
    )
    assert proposal.entry == EntryZone(_q("24378"), _q("24388"))


def test_proposal_text_keeps_every_digit_and_sign_and_is_deterministic() -> None:
    """Worst entry 0.25: risk 0.25 + 1.000000000000000000001, reward 3 - 0.25."""
    levels = {"low": "-0.5", "high": "0.25", "stop": "-1.000000000000000000001", "target": "3"}
    measured = RewardToRisk(Decimal("2.75"), Decimal("1.250000000000000000001"))

    text = str(_proposal(**levels, reward_to_risk=measured))

    assert "entry [-0.5, 0.25] stop -1.000000000000000000001 target 3 " in text
    assert "reward:risk 2.75:1.250000000000000000001 " in text
    assert not _SCIENTIFIC.search(text)
    assert text == str(_proposal(**levels, reward_to_risk=measured))


# ---------------------------------------------------------------------------
# J-3 -- a rounded movement-unit display is labelled
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "total, changes, expected",
    [
        ("380", 19, "20 over 19 changes"),
        (
            "383",
            19,
            "20.15789473684210526315789474 (rounded to 28 significant digits) over 19 changes",
        ),
        (
            "1",
            3,
            "0.3333333333333333333333333333 (rounded to 28 significant digits) over 3 changes",
        ),
        ("0.0000019", 19, "0.0000001 over 19 changes"),
        (
            "0.0000001",
            3,
            "0.00000003333333333333333333333333333 "
            "(rounded to 28 significant digits) over 3 changes",
        ),
        ("1E-10", 1, "0.0000000001 over 1 changes"),
    ],
    ids=["exact", "repeating", "one-third", "small-exact", "small-repeating", "tiny-exact"],
)
def test_movement_unit_text_labels_rounding_only_when_rounded(
    total: str, changes: int, expected: str
) -> None:
    unit = PriceMovementUnit(Decimal(total), changes)

    assert str(unit) == expected
    assert unit.total_absolute_change == Decimal(total)


def test_labelling_leaves_decimal_contexts_untouched() -> None:
    with decimal.localcontext() as caller:
        caller.clear_flags()
        str(PriceMovementUnit(Decimal("383"), 19))
        assert _no_flags(caller)
    for context in _module_contexts():
        assert _no_flags(context)
