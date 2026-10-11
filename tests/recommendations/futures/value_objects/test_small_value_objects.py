"""Tests for the small futures trade recommendation value objects.

TradeDirection, FuturesTradeRecommendationIdentity, RecommendationPolicyVersion,
EntryZone, StopLoss and PriceTarget each carry one or two fields and one rule.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from northstar_core.derivatives import QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.paper_trading import OrderSide
from northstar_core.recommendations.futures import (
    EntryZone,
    FuturesTradeRecommendationIdentity,
    InvalidEntryZoneError,
    InvalidFuturesTradeRecommendationIdentityError,
    InvalidPriceTargetError,
    InvalidRecommendationPolicyVersionError,
    InvalidStopLossError,
    PriceTarget,
    RecommendationPolicyVersion,
    StopLoss,
    TradeDirection,
)
from northstar_core.strategy import RecommendationAction


def _quote(value: str) -> QuoteValue:
    return QuoteValue(Decimal(value))


# ---------------------------------------------------------------------------
# TradeDirection
# ---------------------------------------------------------------------------


def test_trade_direction_is_exactly_long_and_short() -> None:
    assert [direction.value for direction in TradeDirection] == ["LONG", "SHORT"]


def test_trade_direction_shares_no_value_with_research_actions_or_order_sides() -> None:
    """LONG and SHORT are not BUY, SELL or HOLD under another name (ADR-017)."""
    directions = {direction.value for direction in TradeDirection}

    assert directions.isdisjoint({side.value for side in OrderSide})
    assert directions.isdisjoint({"BUY", "SELL", "HOLD"})
    assert RecommendationAction("SELL").value not in directions


@pytest.mark.parametrize("value", ["BUY", "SELL", "HOLD", "long", ""])
def test_trade_direction_refuses_other_vocabularies(value: str) -> None:
    with pytest.raises(ValueError):
        TradeDirection(value)


# ---------------------------------------------------------------------------
# Opaque identity and policy version
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("factory", "error", "attribute"),
    [
        (
            FuturesTradeRecommendationIdentity,
            InvalidFuturesTradeRecommendationIdentityError,
            "identity",
        ),
        (RecommendationPolicyVersion, InvalidRecommendationPolicyVersionError, "version"),
    ],
    ids=["identity", "policy-version"],
)
class TestOpaqueText:
    def test_surrounding_whitespace_is_stripped(self, factory, error, attribute) -> None:
        assert getattr(factory("  rec-nifty-1  "), attribute) == "rec-nifty-1"

    def test_values_compare_and_hash_by_canonical_text(self, factory, error, attribute) -> None:
        assert factory(" a ") == factory("a")
        assert hash(factory(" a ")) == hash(factory("a"))
        assert factory("a") != factory("b")

    @pytest.mark.parametrize("value", ["", "   ", "\t\n"])
    def test_empty_text_is_rejected(self, factory, error, attribute, value: str) -> None:
        with pytest.raises(error, match="cannot be empty"):
            factory(value)

    def test_none_is_rejected(self, factory, error, attribute) -> None:
        with pytest.raises(error, match="cannot be None"):
            factory(None)

    @pytest.mark.parametrize("value", [42, b"rec", ["rec"]])
    def test_non_text_is_rejected(self, factory, error, attribute, value: object) -> None:
        with pytest.raises(error, match="must be a string"):
            factory(value)

    def test_error_is_a_validation_error(self, factory, error, attribute) -> None:
        assert issubclass(error, ValidationError)

    def test_values_are_immutable(self, factory, error, attribute) -> None:
        with pytest.raises(FrozenInstanceError):
            setattr(factory("a"), attribute, "b")

    def test_str_is_the_canonical_text(self, factory, error, attribute) -> None:
        assert str(factory(" a ")) == "a"


def test_identity_and_policy_version_are_distinct_types() -> None:
    assert FuturesTradeRecommendationIdentity("x") != RecommendationPolicyVersion("x")


def test_repr_names_the_type() -> None:
    assert repr(FuturesTradeRecommendationIdentity("r1")) == (
        "FuturesTradeRecommendationIdentity(identity='r1')"
    )
    assert repr(RecommendationPolicyVersion("p1")) == "RecommendationPolicyVersion(version='p1')"


# ---------------------------------------------------------------------------
# EntryZone
# ---------------------------------------------------------------------------


def test_entry_zone_keeps_its_bounds_exactly() -> None:
    zone = EntryZone(_quote("25000.05"), _quote("25100.10"))

    assert zone.low == _quote("25000.05")
    assert zone.high == _quote("25100.1")


def test_a_single_price_entry_zone_is_valid() -> None:
    zone = EntryZone(_quote("25000"), _quote("25000.00"))

    assert zone.low == zone.high


def test_entry_zone_low_above_high_is_rejected() -> None:
    with pytest.raises(InvalidEntryZoneError, match="less than or equal"):
        EntryZone(_quote("25100"), _quote("25000"))


@pytest.mark.parametrize(
    ("low", "high"),
    [(None, "1"), ("1", None), (25000.0, "1"), (Decimal("1"), "1"), ("1", 25000)],
)
def test_entry_zone_bounds_must_be_quote_values(low: object, high: object) -> None:
    low_value = _quote(low) if isinstance(low, str) else low
    high_value = _quote(high) if isinstance(high, str) else high

    with pytest.raises(InvalidEntryZoneError, match="must be a QuoteValue"):
        EntryZone(low_value, high_value)


def test_entry_zone_equality_hashing_and_immutability() -> None:
    zone = EntryZone(_quote("1.0"), _quote("2"))

    assert zone == EntryZone(_quote("1"), _quote("2.00"))
    assert hash(zone) == hash(EntryZone(_quote("1"), _quote("2.00")))
    with pytest.raises(FrozenInstanceError):
        zone.low = _quote("0")  # type: ignore[misc]


def test_entry_zone_text() -> None:
    zone = EntryZone(_quote("1"), _quote("2"))

    assert str(zone) == "1-2"
    assert repr(zone) == (
        "EntryZone(low=QuoteValue(value=Decimal('1')), high=QuoteValue(value=Decimal('2')))"
    )


# ---------------------------------------------------------------------------
# StopLoss and PriceTarget
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("factory", "error"),
    [(StopLoss, InvalidStopLossError), (PriceTarget, InvalidPriceTargetError)],
    ids=["stop", "target"],
)
class TestFixedLevel:
    def test_keeps_the_price_exactly_without_rounding(self, factory, error) -> None:
        assert factory(_quote("24800.0500")).price == _quote("24800.05")

    def test_negative_quotations_are_valid_levels(self, factory, error) -> None:
        assert factory(_quote("-37.63")).price == _quote("-37.63")

    @pytest.mark.parametrize("value", [None, 24800.0, Decimal("24800"), "24800"])
    def test_price_must_be_a_quote_value(self, factory, error, value: object) -> None:
        with pytest.raises(error, match="must be a QuoteValue"):
            factory(value)

    def test_equality_hashing_and_immutability(self, factory, error) -> None:
        level = factory(_quote("1"))

        assert level == factory(_quote("1.0"))
        assert hash(level) == hash(factory(_quote("1.0")))
        with pytest.raises(FrozenInstanceError):
            level.price = _quote("2")

    def test_str_is_the_price(self, factory, error) -> None:
        assert str(factory(_quote("24800.5"))) == "24800.5"


def test_stop_and_target_at_the_same_price_are_different_values() -> None:
    assert StopLoss(_quote("1")) != PriceTarget(_quote("1"))
