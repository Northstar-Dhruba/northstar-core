"""Tests for the futures trade setup and the values it is built from.

Covers FuturesResearchDecisionReference, RecommendationValidity and
FuturesTradeRecommendation: construction, every invariant (including boundary
equality for LONG and SHORT), temporal relationships, equality, hashing,
immutability and text.
"""

from __future__ import annotations

import dataclasses
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from northstar_core.derivatives import ExpirationDate, QuoteValue
from northstar_core.foundation.value_objects import ExchangeCode, PointInTime, Symbol, Timeframe
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.recommendations.futures import (
    EntryZone,
    FuturesResearchDecisionReference,
    FuturesTradeRecommendation,
    FuturesTradeRecommendationIdentity,
    InvalidFuturesResearchDecisionReferenceError,
    InvalidFuturesTradeRecommendationError,
    InvalidRecommendationValidityError,
    PriceTarget,
    RecommendationPolicyVersion,
    RecommendationValidity,
    StopLoss,
    TradeDirection,
)
from northstar_core.strategy import ExplanationReason, StrategyIdentity

_NIFTY = FuturesProductReference(Symbol("NIFTY"), ExchangeCode("NSE"))
_OCT = FuturesContract(_NIFTY, ExpirationDate("2026-10-27"))
_NOV = FuturesContract(_NIFTY, ExpirationDate("2026-11-24"))
_DAILY = Timeframe("1d")
_STRATEGY = StrategyIdentity("directional-mvp-v1")

_DECIDED = PointInTime("2026-10-05T10:00:00Z")
_ISSUED = PointInTime("2026-10-05T12:00:00Z")
_ELIGIBLE = PointInTime("2026-10-06T10:00:00Z")
_VALID_THROUGH = PointInTime("2026-10-09T10:00:00Z")
_CUTOFF = PointInTime("2026-10-27T10:00:00Z")


def _quote(value: str) -> QuoteValue:
    return QuoteValue(Decimal(value))


def _source(**overrides: object) -> FuturesResearchDecisionReference:
    fields: dict[str, object] = {
        "contract": _OCT,
        "timeframe": _DAILY,
        "decision_instant": _DECIDED,
        "strategy_identity": _STRATEGY,
    }
    fields.update(overrides)
    return FuturesResearchDecisionReference(**fields)  # type: ignore[arg-type]


def _long(**overrides: object) -> FuturesTradeRecommendation:
    fields: dict[str, object] = {
        "identity": FuturesTradeRecommendationIdentity("rec-nifty-oct-1"),
        "contract": _OCT,
        "direction": TradeDirection.LONG,
        "entry": EntryZone(_quote("25000"), _quote("25100")),
        "stop": StopLoss(_quote("24800")),
        "target": PriceTarget(_quote("25500")),
        "validity": RecommendationValidity(_ELIGIBLE, _VALID_THROUGH, _CUTOFF),
        "source": _source(),
        "policy_version": RecommendationPolicyVersion("levels-v1"),
        "issued_at": _ISSUED,
        "thesis": (ExplanationReason("Short average above long average", ("strong bullish",)),),
    }
    fields.update(overrides)
    return FuturesTradeRecommendation(**fields)  # type: ignore[arg-type]


def _short(**overrides: object) -> FuturesTradeRecommendation:
    fields: dict[str, object] = {
        "direction": TradeDirection.SHORT,
        "stop": StopLoss(_quote("25300")),
        "target": PriceTarget(_quote("24600")),
    }
    fields.update(overrides)
    return _long(**fields)


# ---------------------------------------------------------------------------
# FuturesResearchDecisionReference
# ---------------------------------------------------------------------------


def test_reference_natural_key_is_the_frozen_record_key() -> None:
    assert _source().natural_key == (_OCT, _DAILY, _DECIDED, _STRATEGY)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("contract", None),
        ("contract", "NIFTY@NSE 2026-10-27"),
        ("timeframe", "1d"),
        ("decision_instant", "2026-10-05T10:00:00Z"),
        ("strategy_identity", "directional-mvp-v1"),
    ],
)
def test_reference_fields_must_have_their_domain_types(field: str, value: object) -> None:
    with pytest.raises(InvalidFuturesResearchDecisionReferenceError, match="must be a"):
        _source(**{field: value})


def test_reference_equality_hashing_and_immutability() -> None:
    assert _source() == _source()
    assert hash(_source()) == hash(_source())
    assert _source() != _source(decision_instant=PointInTime("2026-10-06T10:00:00Z"))
    with pytest.raises(FrozenInstanceError):
        _source().contract = _NOV  # type: ignore[misc]


def test_reference_text() -> None:
    assert str(_source()) == (
        "NIFTY@NSE 2026-10-27 1d decided at 2026-10-05T10:00:00Z by directional-mvp-v1"
    )
    assert repr(_source()).startswith("FuturesResearchDecisionReference(contract=")


# ---------------------------------------------------------------------------
# RecommendationValidity
# ---------------------------------------------------------------------------


def test_validity_may_end_before_the_contract_cutoff() -> None:
    validity = RecommendationValidity(_ELIGIBLE, _VALID_THROUGH, _CUTOFF)

    assert not validity.ends_at_contract_cutoff


def test_validity_may_end_exactly_at_the_contract_cutoff() -> None:
    validity = RecommendationValidity(_ELIGIBLE, _CUTOFF, PointInTime("2026-10-27T15:30:00+05:30"))

    assert validity.ends_at_contract_cutoff


def test_validity_cannot_outlast_the_contract_cutoff() -> None:
    with pytest.raises(InvalidRecommendationValidityError, match="beyond the contract cutoff"):
        RecommendationValidity(_ELIGIBLE, PointInTime("2026-10-28T10:00:00Z"), _CUTOFF)


def test_validity_compares_instants_not_text() -> None:
    """One microsecond later in another offset is still later."""
    with pytest.raises(InvalidRecommendationValidityError):
        RecommendationValidity(_ELIGIBLE, PointInTime("2026-10-27T15:30:00.000001+05:30"), _CUTOFF)


def test_eligible_from_may_equal_valid_through() -> None:
    """B1-11: a window of exactly one eligible observation."""
    validity = RecommendationValidity(_VALID_THROUGH, _VALID_THROUGH, _CUTOFF)

    assert validity.eligible_from == validity.valid_through


def test_eligible_from_after_valid_through_is_rejected() -> None:
    """B1-10."""
    with pytest.raises(InvalidRecommendationValidityError, match="eligible from cannot be later"):
        RecommendationValidity(PointInTime("2026-10-09T10:00:00.000001Z"), _VALID_THROUGH, _CUTOFF)


@pytest.mark.parametrize(
    ("eligible_from", "valid_through", "cutoff"),
    [
        (None, _VALID_THROUGH, _CUTOFF),
        (_ELIGIBLE, None, _CUTOFF),
        (_ELIGIBLE, _VALID_THROUGH, None),
        ("2026-10-06T10:00:00Z", _VALID_THROUGH, _CUTOFF),
        (_ELIGIBLE, "2026-10-09T10:00:00Z", _CUTOFF),
    ],
)
def test_validity_instants_must_be_point_in_time(
    eligible_from: object, valid_through: object, cutoff: object
) -> None:
    with pytest.raises(InvalidRecommendationValidityError, match="must be a PointInTime"):
        RecommendationValidity(eligible_from, valid_through, cutoff)  # type: ignore[arg-type]


def test_validity_equality_and_text() -> None:
    validity = RecommendationValidity(_ELIGIBLE, _VALID_THROUGH, _CUTOFF)

    assert validity == RecommendationValidity(_ELIGIBLE, _VALID_THROUGH, _CUTOFF)
    assert hash(validity) == hash(RecommendationValidity(_ELIGIBLE, _VALID_THROUGH, _CUTOFF))
    assert validity != RecommendationValidity(_VALID_THROUGH, _VALID_THROUGH, _CUTOFF)
    assert str(validity) == (
        "from 2026-10-06T10:00:00Z through 2026-10-09T10:00:00Z "
        "(contract cutoff 2026-10-27T10:00:00Z)"
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_a_valid_long_setup_is_constructed() -> None:
    recommendation = _long()

    assert recommendation.direction is TradeDirection.LONG
    assert recommendation.strategy_identity == _STRATEGY
    assert recommendation.contract == _OCT


def test_a_valid_short_setup_is_constructed() -> None:
    assert _short().direction is TradeDirection.SHORT


def test_a_single_price_entry_zone_is_accepted() -> None:
    zone = EntryZone(_quote("25050"), _quote("25050"))

    assert _long(entry=zone).entry == zone
    assert _short(entry=zone).entry == zone


def test_the_setup_carries_no_status_or_execution_fields() -> None:
    names = {field.name for field in dataclasses.fields(FuturesTradeRecommendation)}

    assert names == {
        "identity",
        "contract",
        "direction",
        "entry",
        "stop",
        "target",
        "validity",
        "source",
        "policy_version",
        "issued_at",
        "thesis",
    }


# ---------------------------------------------------------------------------
# Price invariants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stop", "target", "message"),
    [
        ("25000", "25500", "stop must be below the entry zone"),
        ("25050", "25500", "stop must be below the entry zone"),
        ("26000", "25500", "stop must be below the entry zone"),
        ("24800", "25100", "target must be above the entry zone"),
        ("24800", "25050", "target must be above the entry zone"),
        ("24800", "24000", "target must be above the entry zone"),
    ],
    ids=[
        "stop-equals-entry-low",
        "stop-inside-zone",
        "stop-above-target",
        "target-equals-entry-high",
        "target-inside-zone",
        "target-below-stop",
    ],
)
def test_long_price_order_is_strict(stop: str, target: str, message: str) -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationError, match=message):
        _long(stop=StopLoss(_quote(stop)), target=PriceTarget(_quote(target)))


@pytest.mark.parametrize(
    ("stop", "target", "message"),
    [
        ("25100", "24600", "stop must be above the entry zone"),
        ("25050", "24600", "stop must be above the entry zone"),
        ("24000", "24600", "stop must be above the entry zone"),
        ("25300", "25000", "target must be below the entry zone"),
        ("25300", "25050", "target must be below the entry zone"),
        ("25300", "26000", "target must be below the entry zone"),
    ],
    ids=[
        "stop-equals-entry-high",
        "stop-inside-zone",
        "stop-below-target",
        "target-equals-entry-low",
        "target-inside-zone",
        "target-above-stop",
    ],
)
def test_short_price_order_is_strict(stop: str, target: str, message: str) -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationError, match=message):
        _short(stop=StopLoss(_quote(stop)), target=PriceTarget(_quote(target)))


def test_long_levels_are_not_valid_for_short() -> None:
    """The same numbers cannot describe both directions."""
    with pytest.raises(InvalidFuturesTradeRecommendationError):
        _long(direction=TradeDirection.SHORT)


def test_levels_one_smallest_step_apart_are_valid() -> None:
    """No tick is assumed: only strict ordering of exact decimals."""
    recommendation = _long(
        entry=EntryZone(_quote("25000.0001"), _quote("25000.0002")),
        stop=StopLoss(_quote("25000")),
        target=PriceTarget(_quote("25000.0003")),
    )

    assert recommendation.target.price == _quote("25000.0003")


# ---------------------------------------------------------------------------
# Source, timing and thesis invariants
# ---------------------------------------------------------------------------


def test_source_decision_must_be_for_the_recommended_contract() -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationError, match="recommended contract"):
        _long(source=_source(contract=_NOV))


@pytest.mark.parametrize("timeframe", ["1h", "1w", "1m"])
def test_source_decision_must_be_daily(timeframe: str) -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationError, match="1d timeframe"):
        _long(source=_source(timeframe=Timeframe(timeframe)))


def test_issuance_at_the_decision_instant_is_valid() -> None:
    assert _long(issued_at=_DECIDED).issued_at == _DECIDED


def test_issuance_before_the_source_decision_is_rejected() -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationError, match="before its source decision"):
        _long(issued_at=PointInTime("2026-10-05T09:59:59Z"))


@pytest.mark.parametrize(
    "issued_at",
    [
        "2026-10-06T10:00:00Z",
        "2026-10-06T15:30:00+05:30",
        "2026-10-07T00:00:00Z",
        "2026-10-10T00:00:00Z",
    ],
    ids=[
        "at-eligible-from",
        "same-instant-other-offset",
        "after-eligible-from",
        "after-valid-through",
    ],
)
def test_issuance_must_precede_the_first_eligible_observation(issued_at: str) -> None:
    """B1-9: issued_at equal to eligible_from is rejected."""
    with pytest.raises(InvalidFuturesTradeRecommendationError, match="first eligible observation"):
        _long(issued_at=PointInTime(issued_at))


def test_issuance_just_before_eligible_from_is_valid() -> None:
    issued_at = PointInTime("2026-10-06T09:59:59.999999Z")

    assert _long(issued_at=issued_at).issued_at == issued_at


def test_thesis_must_not_be_empty() -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationError, match="at least one"):
        _long(thesis=())


@pytest.mark.parametrize(
    "thesis",
    [["reason"], ("reason",), (ExplanationReason("ok"), "reason"), None],
    ids=["list", "strings", "mixed", "none"],
)
def test_thesis_must_be_a_tuple_of_explanation_reasons(thesis: object) -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationError, match="thesis"):
        _long(thesis=thesis)


# ---------------------------------------------------------------------------
# Field types
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("identity", "rec-nifty-oct-1"),
        ("contract", "NIFTY@NSE 2026-10-27"),
        ("direction", "LONG"),
        ("direction", "BUY"),
        ("entry", (_quote("25000"), _quote("25100"))),
        ("stop", _quote("24800")),
        ("target", _quote("25500")),
        ("validity", _VALID_THROUGH),
        ("source", _OCT),
        ("policy_version", "levels-v1"),
        ("issued_at", "2026-10-05T12:00:00Z"),
        ("identity", None),
    ],
)
def test_every_field_requires_its_exact_domain_type(field: str, value: object) -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationError, match="must be a"):
        _long(**{field: value})


def test_a_research_action_is_not_accepted_as_a_direction() -> None:
    from northstar_core.strategy import RecommendationAction

    with pytest.raises(InvalidFuturesTradeRecommendationError, match="TradeDirection"):
        _long(direction=RecommendationAction("BUY"))


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_equal_setups_compare_and_hash_alike() -> None:
    assert _long() == _long()
    assert hash(_long()) == hash(_long())


def test_any_differing_field_makes_a_different_setup() -> None:
    assert _long() != _long(identity=FuturesTradeRecommendationIdentity("rec-nifty-oct-2"))
    assert _long() != _long(policy_version=RecommendationPolicyVersion("levels-v2"))
    assert _long() != _long(thesis=(ExplanationReason("Different rationale"),))


def test_the_setup_is_immutable() -> None:
    recommendation = _long()

    with pytest.raises(FrozenInstanceError):
        recommendation.stop = StopLoss(_quote("24000"))  # type: ignore[misc]


def test_text_summarises_the_setup() -> None:
    assert str(_long()) == (
        "rec-nifty-oct-1: LONG NIFTY@NSE 2026-10-27 entry 25000-25100 stop 24800 "
        "target 25500 issued 2026-10-05T12:00:00Z valid 2026-10-09T10:00:00Z"
    )
    assert repr(_long()).startswith("FuturesTradeRecommendation(identity=")
