"""EI-4B equity value objects: synthetic inputs, references, levels, sizing, timing.

Every value is a clearly labelled synthetic example. None is an exchange fact,
a broker tariff or an approved trading parameter.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import date, datetime
from decimal import Decimal

import pytest

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    Currency,
    ExchangeCode,
    Money,
    PointInTime,
    Price,
    Symbol,
)
from northstar_core.recommendations.equity import (
    EquityCostSide,
    EquityEntryZone,
    EquityIssuanceKind,
    EquityPriceIncrement,
    EquityRecommendationDefinition,
    EquityRecommendationDirection,
    EquityRecommendationLevels,
    EquityRecommendationRejection,
    EquityRecommendationRejectionReason,
    EquityRecommendationTiming,
    EquityResearchCandidateReference,
    EquitySyntheticCostComponent,
    EquitySyntheticCostSchedule,
    EquitySyntheticGenerationPolicy,
    EquitySyntheticRiskPolicy,
    EquitySyntheticSizing,
    EquitySyntheticVersion,
    InvalidEquityPriceIncrementError,
    InvalidEquityRecommendationDefinitionError,
    InvalidEquityRecommendationLevelsError,
    InvalidEquityRecommendationRejectionError,
    InvalidEquityRecommendationTimingError,
    InvalidEquityResearchCandidateReferenceError,
    InvalidEquitySyntheticCostScheduleError,
    InvalidEquitySyntheticGenerationPolicyError,
    InvalidEquitySyntheticRiskPolicyError,
    InvalidEquitySyntheticSizingError,
    InvalidEquitySyntheticVersionError,
    form_equity_recommendation,
)
from northstar_core.strategy import StrategyIdentity

_INR = Currency("INR")
_REASON = EquityRecommendationRejectionReason


def _v(name: str) -> EquitySyntheticVersion:
    return EquitySyntheticVersion(f"synthetic-{name}")


def _inr(amount: str) -> Price:
    return Price(Decimal(amount), _INR)


def _policy(**changes: object) -> EquitySyntheticGenerationPolicy:
    values: dict[str, object] = {
        "version": _v("generation/1"),
        "entry_offset_below": Decimal("0.01"),
        "entry_offset_above": Decimal("0"),
        "target_risk_multiple": Decimal("2"),
        "minimum_net_reward_to_risk": Decimal("1"),
    }
    values.update(changes)
    return EquitySyntheticGenerationPolicy(**values)  # type: ignore[arg-type]


def _risk(**changes: object) -> EquitySyntheticRiskPolicy:
    values: dict[str, object] = {
        "version": _v("risk/1"),
        "model_capital": Money(Decimal("10000"), _INR),
        "risk_fraction": Decimal("0.1"),
        "exposure_fraction": Decimal("1"),
    }
    values.update(changes)
    return EquitySyntheticRiskPolicy(**values)  # type: ignore[arg-type]


def _component(side: EquityCostSide, **changes: object) -> EquitySyntheticCostComponent:
    values: dict[str, object] = {
        "label": f"synthetic-{side.value.lower()}-fee",
        "side": side,
        "proportional_rate": Decimal("0"),
        "per_share": Decimal("0"),
        "per_order": Decimal("0"),
    }
    values.update(changes)
    return EquitySyntheticCostComponent(**values)  # type: ignore[arg-type]


def _schedule(**changes: object) -> EquitySyntheticCostSchedule:
    values: dict[str, object] = {
        "version": _v("costs/1"),
        "currency": _INR,
        "components": (_component(EquityCostSide.ENTRY), _component(EquityCostSide.EXIT)),
        "slippage_rate_per_side": Decimal("0"),
        "rounding_increment": Decimal("0.01"),
    }
    values.update(changes)
    return EquitySyntheticCostSchedule(**values)  # type: ignore[arg-type]


def _reference(**changes: object) -> EquityResearchCandidateReference:
    values: dict[str, object] = {
        "strategy": StrategyIdentity("synthetic-orb"),
        "research_configuration_version": _v("research/1"),
        "listing": ListingReference(Symbol("M&M"), ExchangeCode("NSE")),
        "trading_date": date(2026, 8, 12),
        "decision_as_of": PointInTime("2026-08-12T04:06:00Z"),
        "research_decision_fingerprint": "eir1-sha256:" + "a" * 64,
        "candidate_entry_fingerprint": "eirt1-sha256:" + "b" * 64,
        "evidence_snapshot_id": "ecs1-sha256:" + "c" * 64,
    }
    values.update(changes)
    return EquityResearchCandidateReference(**values)  # type: ignore[arg-type]


def _definition() -> EquityRecommendationDefinition:
    result = form_equity_recommendation(
        _reference(),
        _inr("100"),
        _inr("90"),
        _policy(),
        _risk(),
        EquityPriceIncrement(Decimal("1"), _v("increment/1")),
        _schedule(),
    )
    assert isinstance(result, EquityRecommendationDefinition)
    return result


# -- versions and synthetic inputs (C, D, V, W) ----------------------------------------


@pytest.mark.parametrize(
    "value", ["", "x", "synthetic-", " synthetic-x", "synthetic-x ", "production-1", 7, None]
)
def test_a_synthetic_version_must_be_visibly_synthetic(value: object) -> None:
    with pytest.raises(InvalidEquitySyntheticVersionError):
        EquitySyntheticVersion(value)  # type: ignore[arg-type]


def test_a_synthetic_version_keeps_its_text() -> None:
    assert str(_v("generation/1")) == "synthetic-generation/1"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("entry_offset_below", 0.001),
        ("entry_offset_below", 1),
        ("entry_offset_below", "0.001"),
        ("entry_offset_below", True),
        ("entry_offset_below", Decimal("NaN")),
        ("entry_offset_below", Decimal("Infinity")),
        ("entry_offset_below", Decimal("-0.001")),
        ("entry_offset_below", Decimal("1")),
        ("entry_offset_above", Decimal("-1")),
        ("target_risk_multiple", Decimal("0")),
        ("minimum_net_reward_to_risk", Decimal("0")),
        ("version", "synthetic-generation/1"),
    ],
)
def test_the_generation_policy_refuses_invalid_or_non_decimal_values(
    field: str, value: object
) -> None:
    with pytest.raises(InvalidEquitySyntheticGenerationPolicyError):
        _policy(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_capital", Money(Decimal("0"), _INR)),
        ("model_capital", Money(Decimal("-1"), _INR)),
        ("model_capital", Decimal("10000")),
        ("risk_fraction", Decimal("0")),
        ("risk_fraction", Decimal("1.01")),
        ("risk_fraction", 0.1),
        ("exposure_fraction", Decimal("2")),
        ("exposure_fraction", Decimal("-0.5")),
    ],
)
def test_the_risk_policy_refuses_invalid_values(field: str, value: object) -> None:
    with pytest.raises(InvalidEquitySyntheticRiskPolicyError):
        _risk(**{field: value})


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-0.05"), 0.05, 1, "0.05"])
def test_the_price_increment_must_be_a_positive_decimal(amount: object) -> None:
    with pytest.raises(InvalidEquityPriceIncrementError):
        EquityPriceIncrement(amount, _v("increment/1"))  # type: ignore[arg-type]


def test_nothing_has_a_default() -> None:
    for kind in (
        EquitySyntheticGenerationPolicy,
        EquitySyntheticRiskPolicy,
        EquityPriceIncrement,
        EquitySyntheticCostSchedule,
        EquitySyntheticCostComponent,
    ):
        with pytest.raises(TypeError):
            kind()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        EquitySyntheticGenerationPolicy(  # type: ignore[call-arg]
            version=_v("generation/1"),
            entry_offset_below=Decimal("0"),
            entry_offset_above=Decimal("0"),
            target_risk_multiple=Decimal("2"),
        )


def test_decimals_are_canonicalized_and_documents_are_deterministic() -> None:
    spelled = _policy(entry_offset_above=Decimal("0.0010"), target_risk_multiple=Decimal("2.00"))
    plain = _policy(entry_offset_above=Decimal("0.001"), target_risk_multiple=Decimal("2"))
    assert spelled == plain
    assert (
        spelled.document()
        == plain.document()
        == {
            "version": "synthetic-generation/1",
            "entry_offset_below": "0.01",
            "entry_offset_above": "0.001",
            "target_risk_multiple": "2",
            "minimum_net_reward_to_risk": "1",
        }
    )
    assert _risk().document() == {
        "version": "synthetic-risk/1",
        "model_capital": "10000",
        "currency": "INR",
        "risk_fraction": "0.1",
        "exposure_fraction": "1",
    }
    first = json.dumps(_definition().document(), sort_keys=True)
    assert first == json.dumps(_definition().document(), sort_keys=True)


# -- cost schedule (R, S, U) ------------------------------------------------------------


def test_a_cost_schedule_must_state_both_sides_explicitly() -> None:
    with pytest.raises(InvalidEquitySyntheticCostScheduleError, match="ENTRY and one EXIT"):
        _schedule(components=(_component(EquityCostSide.ENTRY),))
    with pytest.raises(InvalidEquitySyntheticCostScheduleError, match="unique"):
        _schedule(
            components=(
                _component(EquityCostSide.ENTRY),
                _component(EquityCostSide.ENTRY),
                _component(EquityCostSide.EXIT),
            )
        )
    with pytest.raises(InvalidEquitySyntheticCostScheduleError):
        _component(EquityCostSide.ENTRY, per_order=Decimal("-1"))
    with pytest.raises(InvalidEquitySyntheticCostScheduleError):
        _component(EquityCostSide.ENTRY, proportional_rate=0.001)
    with pytest.raises(InvalidEquitySyntheticCostScheduleError):
        _schedule(rounding_increment=Decimal("0"))


def test_a_per_order_amount_is_never_spread_per_share() -> None:
    schedule = _schedule(
        components=(
            _component(EquityCostSide.ENTRY, per_order=Decimal("15")),
            _component(EquityCostSide.EXIT),
        )
    )
    assert schedule.cost(EquityCostSide.ENTRY, _inr("100"), 1) == Decimal("15")
    assert schedule.cost(EquityCostSide.ENTRY, _inr("100"), 10) == Decimal("15")
    assert schedule.cost(EquityCostSide.EXIT, _inr("100"), 10) == Decimal("0")


def test_costs_combine_exactly_and_round_up_to_the_schedule_increment() -> None:
    schedule = _schedule(
        components=(
            _component(
                EquityCostSide.ENTRY,
                proportional_rate=Decimal("0.001"),
                per_share=Decimal("0.01"),
                per_order=Decimal("10"),
            ),
            _component(EquityCostSide.EXIT, proportional_rate=Decimal("0.002")),
        ),
        slippage_rate_per_side=Decimal("0.0005"),
    )
    # 0.001*1000 + 0.01*10 + 10 + slippage 0.0005*1000 = 1 + 0.1 + 10 + 0.5
    assert schedule.cost(EquityCostSide.ENTRY, _inr("100"), 10) == Decimal("11.6")
    # 0.002*1003.3 + 0.0005*1003.3 = 2.50825, rounded up to 2.51
    assert schedule.cost(EquityCostSide.EXIT, _inr("100.33"), 10) == Decimal("2.51")
    coarse = _schedule(
        components=(
            _component(EquityCostSide.ENTRY, proportional_rate=Decimal("0.003")),
            _component(EquityCostSide.EXIT),
        ),
        rounding_increment=Decimal("1"),
    )
    assert coarse.cost(EquityCostSide.ENTRY, _inr("100"), 1) == Decimal("1")  # 0.3 -> 1


def test_cost_estimation_refuses_misuse() -> None:
    schedule = _schedule()
    with pytest.raises(InvalidEquitySyntheticCostScheduleError):
        schedule.cost(EquityCostSide.ENTRY, Price(Decimal("100"), Currency("USD")), 1)
    for quantity in (0, -1, True):
        with pytest.raises(InvalidEquitySyntheticCostScheduleError):
            schedule.cost(EquityCostSide.ENTRY, _inr("100"), quantity)  # type: ignore[arg-type]


# -- the research reference -------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("research_decision_fingerprint", "eirt1-sha256:" + "a" * 64),
        ("research_decision_fingerprint", "eir1-sha256:" + "A" * 64),
        ("candidate_entry_fingerprint", "eir1-sha256:" + "b" * 64),
        ("candidate_entry_fingerprint", "eirt1-sha256:" + "b" * 63),
        ("evidence_snapshot_id", "ecm1-sha256:" + "c" * 64),
        ("trading_date", datetime(2026, 8, 12)),
        ("research_configuration_version", "synthetic-research/1"),
        ("decision_as_of", "2026-08-12T04:06:00Z"),
    ],
)
def test_the_research_reference_checks_its_shape(field: str, value: object) -> None:
    with pytest.raises(InvalidEquityResearchCandidateReferenceError):
        _reference(**{field: value})


# -- levels (H, I, X) -------------------------------------------------------------------


def test_an_inverted_or_non_positive_zone_is_refused() -> None:
    with pytest.raises(InvalidEquityRecommendationLevelsError, match="inverted"):
        EquityEntryZone(_inr("101"), _inr("100"))
    with pytest.raises(InvalidEquityRecommendationLevelsError, match="positive"):
        EquityEntryZone(_inr("0"), _inr("1"))
    with pytest.raises(InvalidEquityRecommendationLevelsError, match="currency"):
        EquityEntryZone(_inr("100"), Price(Decimal("101"), Currency("USD")))
    with pytest.raises(InvalidEquityRecommendationLevelsError, match="collapsed"):
        EquityEntryZone(_inr("100"), _inr("100"))
    assert EquityEntryZone(_inr("99.95"), _inr("100")).high == _inr("100")


@pytest.mark.parametrize(
    ("stop", "target", "match"),
    [
        ("100", "120", "below"),
        ("100.5", "120", "below"),
        ("0", "120", "positive"),
        ("90", "101", "above"),
        ("90", "100", "above"),
    ],
)
def test_levels_require_stop_below_the_whole_zone_and_target_above_worst_entry(
    stop: str, target: str, match: str
) -> None:
    zone = EquityEntryZone(_inr("100"), _inr("101"))
    with pytest.raises(InvalidEquityRecommendationLevelsError, match=match):
        EquityRecommendationLevels(zone, _inr(stop), _inr(target))


def test_levels_measure_from_the_worst_entry() -> None:
    levels = EquityRecommendationLevels(
        EquityEntryZone(_inr("100"), _inr("101")), _inr("90"), _inr("123")
    )
    assert levels.worst_entry == _inr("101")
    assert (levels.risk_per_share, levels.reward_per_share) == (Decimal("11"), Decimal("22"))


def test_modeled_contracts_carry_no_execution_or_issuance_fields() -> None:
    for kind in (
        EquityEntryZone,
        EquityRecommendationLevels,
        EquitySyntheticSizing,
        EquityRecommendationDefinition,
    ):
        names = {field.name for field in dataclasses.fields(kind)}
        for forbidden in ("fill", "order", "position", "pnl", "profit", "executed", "broker"):
            assert not any(forbidden in name for name in names), (kind, names)
    names = {field.name for field in dataclasses.fields(EquityRecommendationDefinition)}
    assert not names & {"identity", "issued_at", "eligible_from", "status", "lifecycle"}
    assert EquityRecommendationDirection.__members__.keys() == {"LONG"}


# -- immutability and invariants (B) ----------------------------------------------------


def test_every_value_is_immutable() -> None:
    definition = _definition()
    for value, field in (
        (definition, "sizing"),
        (definition.levels, "stop"),
        (definition.sizing, "quantity"),
        (_policy(), "target_risk_multiple"),
        (_risk(), "risk_fraction"),
        (_schedule(), "components"),
        (_reference(), "listing"),
    ):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(value, field, None)


@pytest.mark.parametrize(
    "changes",
    [
        {"quantity": 0},
        {"quantity": True},
        {"net_risk": Decimal("999")},
        {"net_reward": Decimal("1")},
        {"risk_budget": Decimal("999")},
        {"exposure_budget": Decimal("1")},
        {"entry_cost": Decimal("-1")},
        {"gross_risk": 1000.0},
    ],
)
def test_a_sizing_must_be_internally_consistent(changes: dict[str, object]) -> None:
    with pytest.raises(InvalidEquitySyntheticSizingError):
        dataclasses.replace(_definition().sizing, **changes)


def test_a_definition_must_be_consistent_with_its_levels_and_increment() -> None:
    definition = _definition()
    other_levels = EquityRecommendationLevels(
        EquityEntryZone(_inr("99"), _inr("100")), _inr("80"), _inr("120")
    )
    with pytest.raises(InvalidEquityRecommendationDefinitionError, match="measured"):
        dataclasses.replace(definition, levels=other_levels)
    with pytest.raises(InvalidEquityRecommendationDefinitionError, match="multiple"):
        dataclasses.replace(
            definition, price_increment=EquityPriceIncrement(Decimal("7"), _v("increment/2"))
        )
    with pytest.raises(InvalidEquityRecommendationDefinitionError):
        dataclasses.replace(definition, direction="LONG")


def test_a_rejection_needs_ordered_distinct_reasons() -> None:
    reference, version = _reference(), _v("generation/1")
    ok = EquityRecommendationRejection(
        reference, version, (_REASON.INVALID_PRICE, _REASON.INVALID_TARGET)
    )
    assert ok.document()["reasons"] == ["INVALID_PRICE", "INVALID_TARGET"]
    for reasons in (
        (),
        (_REASON.INVALID_TARGET, _REASON.INVALID_PRICE),
        (_REASON.INVALID_PRICE, _REASON.INVALID_PRICE),
        ("INVALID_PRICE",),
    ):
        with pytest.raises(InvalidEquityRecommendationRejectionError):
            EquityRecommendationRejection(reference, version, reasons)  # type: ignore[arg-type]


def test_every_domain_error_is_a_validation_error() -> None:
    for error in (
        InvalidEquitySyntheticVersionError,
        InvalidEquityPriceIncrementError,
        InvalidEquitySyntheticGenerationPolicyError,
        InvalidEquitySyntheticRiskPolicyError,
        InvalidEquitySyntheticCostScheduleError,
        InvalidEquityResearchCandidateReferenceError,
        InvalidEquityRecommendationLevelsError,
        InvalidEquitySyntheticSizingError,
        InvalidEquityRecommendationDefinitionError,
        InvalidEquityRecommendationRejectionError,
        InvalidEquityRecommendationTimingError,
    ):
        assert issubclass(error, ValidationError)


# -- timing (Y) -------------------------------------------------------------------------


def _timing(decision: str, issued: str, eligible: str, kind: EquityIssuanceKind):  # type: ignore[no-untyped-def]
    return EquityRecommendationTiming(
        PointInTime(decision), kind, PointInTime(issued), PointInTime(eligible)
    )


def test_decision_issuance_and_eligibility_are_distinct_and_ordered() -> None:
    timing = _timing(
        "2026-08-12T04:06:00Z",
        "2026-08-12T04:06:30Z",
        "2026-08-12T04:10:00Z",
        EquityIssuanceKind.ACTUAL,
    )
    assert timing.is_actual_issuance
    assert timing.document() == {
        "decision_as_of": "2026-08-12T04:06:00Z",
        "issuance_kind": "ACTUAL",
        "issued_at": "2026-08-12T04:06:30Z",
        "eligible_from": "2026-08-12T04:10:00Z",
    }
    modeled = _timing(
        "2026-08-12T04:06:00Z",
        "2026-08-12T04:06:00Z",
        "2026-08-12T04:06:00Z",
        EquityIssuanceKind.MODELED,
    )
    assert not modeled.is_actual_issuance


@pytest.mark.parametrize(
    ("decision", "issued", "eligible", "match"),
    [
        ("2026-08-12T04:06:00Z", "2026-08-12T04:05:59Z", "2026-08-12T04:10:00Z", "before its"),
        ("2026-08-12T04:06:00Z", "2026-08-12T04:07:00Z", "2026-08-12T04:06:30Z", "before issuance"),
    ],
)
def test_timing_never_runs_backwards(decision: str, issued: str, eligible: str, match: str) -> None:
    with pytest.raises(InvalidEquityRecommendationTimingError, match=match):
        _timing(decision, issued, eligible, EquityIssuanceKind.ACTUAL)
    with pytest.raises(InvalidEquityRecommendationTimingError):
        EquityRecommendationTiming(
            PointInTime(decision),
            "ACTUAL",
            PointInTime(decision),
            PointInTime(decision),  # type: ignore[arg-type]
        )
