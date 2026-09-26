"""Reference contract test suite for the Trade aggregate root.

This suite defines the Northstar Reference Aggregate Contract for Trade.
"""

import pytest

from northstar_core.domain.exchange import Exchange
from northstar_core.domain.instrument import Instrument
from northstar_core.domain.listing import Listing
from northstar_core.domain.value_objects import (
    ListingStatus,
    ParticipantIdentity,
    ParticipantReference,
    Tradability,
)
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    Currency,
    ExchangeCode,
    PointInTime,
    Price,
    Quantity,
    Symbol,
)
from northstar_core.trades import InvalidTradeError, Trade, TradeIdentity


def _build_listing(symbol: str = "AAPL") -> Listing:
    return Listing(
        Instrument(Symbol(symbol), f"{symbol} Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        ListingStatus("Active"),
        Tradability("Permitted"),
    )


def _build_point_in_time(value: str = "2026-08-17T09:30:00Z") -> PointInTime:
    return PointInTime(value)


def _build_trade_identity(value: str = "trade-opaque-001") -> TradeIdentity:
    return TradeIdentity(value)


def _build_quantity(value: str = "10") -> Quantity:
    return Quantity(value)


def _build_price(value: str = "100") -> Price:
    return Price(value, Currency("USD"))


def _build_participant_reference(value: str = "participant-opaque-001") -> ParticipantReference:
    return ParticipantReference(ParticipantIdentity(value))


def _build_trade(
    *,
    trade_identity: TradeIdentity | None = None,
    listing: Listing | None = None,
    point_in_time: PointInTime | None = None,
    quantity: Quantity | None = None,
    price: Price | None = None,
    participant_reference: ParticipantReference | None = None,
) -> Trade:
    return Trade(
        trade_identity or _build_trade_identity(),
        listing or _build_listing(),
        point_in_time or _build_point_in_time(),
        quantity or _build_quantity(),
        price or _build_price(),
        participant_reference or _build_participant_reference(),
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_trade_from_approved_aggregate_composition():
    assert isinstance(_build_trade(), Trade)


def test_construction_preserves_approved_aggregate_composition():
    trade_identity = _build_trade_identity()
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    quantity = _build_quantity()
    price = _build_price()
    participant_reference = _build_participant_reference()

    trade = Trade(trade_identity, listing, point_in_time, quantity, price, participant_reference)

    assert trade.trade_identity is trade_identity
    assert trade.listing is listing
    assert trade.point_in_time is point_in_time
    assert trade.quantity is quantity
    assert trade.price is price
    assert trade.participant_reference is participant_reference


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none_trade_identity():
    with pytest.raises(InvalidTradeError, match="identity cannot be None"):
        Trade(
            None,
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
        )


def test_rejects_none_listing():
    with pytest.raises(InvalidTradeError, match="listing cannot be None"):
        Trade(
            _build_trade_identity(),
            None,
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
        )


def test_rejects_none_point_in_time():
    with pytest.raises(InvalidTradeError, match="point-in-time context cannot be None"):
        Trade(
            _build_trade_identity(),
            _build_listing(),
            None,
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
        )


def test_rejects_none_quantity():
    with pytest.raises(InvalidTradeError, match="quantity cannot be None"):
        Trade(
            _build_trade_identity(),
            _build_listing(),
            _build_point_in_time(),
            None,
            _build_price(),
            _build_participant_reference(),
        )


def test_rejects_none_price():
    with pytest.raises(InvalidTradeError, match="price cannot be None"):
        Trade(
            _build_trade_identity(),
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            None,
            _build_participant_reference(),
        )


def test_rejects_none_participant_reference():
    with pytest.raises(InvalidTradeError, match="participant reference cannot be None"):
        Trade(
            _build_trade_identity(),
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            None,
        )


def test_rejects_invalid_trade_identity_type():
    with pytest.raises(InvalidTradeError, match="identity must be a TradeIdentity"):
        Trade(
            "identity",
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
        )


def test_rejects_invalid_listing_type():
    with pytest.raises(InvalidTradeError, match="listing must be a Listing"):
        Trade(
            _build_trade_identity(),
            "listing",
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
        )


def test_rejects_invalid_point_in_time_type():
    with pytest.raises(InvalidTradeError, match="point-in-time context must be a PointInTime"):
        Trade(
            _build_trade_identity(),
            _build_listing(),
            "time",
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
        )


def test_rejects_invalid_quantity_type():
    with pytest.raises(InvalidTradeError, match="quantity must be a Quantity"):
        Trade(
            _build_trade_identity(),
            _build_listing(),
            _build_point_in_time(),
            "10",
            _build_price(),
            _build_participant_reference(),
        )


def test_rejects_invalid_price_type():
    with pytest.raises(InvalidTradeError, match="price must be a Price"):
        Trade(
            _build_trade_identity(),
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            "100 USD",
            _build_participant_reference(),
        )


def test_rejects_invalid_participant_reference_type():
    with pytest.raises(
        InvalidTradeError, match="participant reference must be a ParticipantReference"
    ):
        Trade(
            _build_trade_identity(),
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            "participant",
        )


def test_invalid_trade_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Trade(
            None,
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
        )


def test_invalid_trade_error_is_a_value_error():
    with pytest.raises(ValueError):
        Trade(
            None,
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
        )


# ---------------------------------------------------------------------------
# Aggregate Composition
# ---------------------------------------------------------------------------


def test_trade_composes_exactly_the_approved_dependencies():
    trade = _build_trade()

    assert isinstance(trade.trade_identity, TradeIdentity)
    assert isinstance(trade.listing, Listing)
    assert isinstance(trade.point_in_time, PointInTime)
    assert isinstance(trade.quantity, Quantity)
    assert isinstance(trade.price, Price)
    assert isinstance(trade.participant_reference, ParticipantReference)


def test_trade_does_not_compose_order_trade_status_portfolio_or_market_data():
    trade = _build_trade()

    assert not hasattr(trade, "order")
    assert not hasattr(trade, "trade_status")
    assert not hasattr(trade, "portfolio")
    assert not hasattr(trade, "quote")
    assert not hasattr(trade, "tick")
    assert not hasattr(trade, "ohlc_bar")
    assert not hasattr(trade, "order_book")
    assert not hasattr(trade, "settlement")
    assert not hasattr(trade, "accounting")


def test_composed_concepts_remain_authoritative_owners_of_business_meaning():
    trade = _build_trade()

    assert trade.trade_identity.identity == "trade-opaque-001"
    assert trade.participant_reference.participant_identity.identity == "participant-opaque-001"
    assert trade.quantity.value == Quantity("10").value
    assert trade.price == Price("100", Currency("USD"))


# ---------------------------------------------------------------------------
# Identity Semantics
# ---------------------------------------------------------------------------


def test_trades_with_same_identity_compare_equal_despite_different_composition():
    left = _build_trade(
        trade_identity=_build_trade_identity("trade-opaque-001"),
        listing=_build_listing("AAPL"),
        point_in_time=_build_point_in_time("2026-08-17T09:30:00Z"),
        quantity=_build_quantity("10"),
        price=_build_price("100"),
        participant_reference=_build_participant_reference("participant-opaque-001"),
    )
    right = _build_trade(
        trade_identity=_build_trade_identity(" trade-opaque-001 "),
        listing=_build_listing("MSFT"),
        point_in_time=_build_point_in_time("2026-08-17T14:30:00+05:00"),
        quantity=_build_quantity("25"),
        price=_build_price("200"),
        participant_reference=_build_participant_reference("participant-opaque-002"),
    )

    assert left == right


def test_trades_with_different_identity_do_not_compare_equal():
    assert _build_trade(trade_identity=_build_trade_identity("trade-opaque-001")) != _build_trade(
        trade_identity=_build_trade_identity("trade-opaque-002")
    )


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_trades_have_equal_hashes_from_trade_identity():
    left = _build_trade(trade_identity=_build_trade_identity("trade-opaque-001"))
    right = _build_trade(trade_identity=_build_trade_identity(" trade-opaque-001 "))

    assert hash(left) == hash(right)


def test_trade_is_usable_as_dictionary_key():
    key = _build_trade(trade_identity=_build_trade_identity("trade-opaque-001"))
    index = {key: "execution"}

    assert (
        index[_build_trade(trade_identity=_build_trade_identity("trade-opaque-001"))] == "execution"
    )


def test_trade_hashing_follows_trade_identity():
    trade = _build_trade()

    assert hash(trade) == hash(trade.trade_identity)


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_repr_contains_trade_and_approved_composed_components():
    representation = repr(_build_trade())

    assert "Trade(" in representation
    assert "TradeIdentity(" in representation
    assert "Listing(" in representation
    assert "ParticipantReference(" in representation


def test_str_returns_deterministic_business_representation():
    trade = _build_trade()

    assert str(trade) == str(_build_trade())
    assert "trade-opaque-001" in str(trade)
    assert "AAPL@NASDAQ" in str(trade)


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_trade_is_immutable():
    trade = _build_trade()

    with pytest.raises(AttributeError):
        trade.quantity = _build_quantity("20")


def test_composed_value_objects_remain_immutable():
    trade = _build_trade()

    with pytest.raises(AttributeError):
        trade.trade_identity.identity = "trade-opaque-002"
    with pytest.raises(AttributeError):
        trade.quantity.value = trade.quantity.value
    with pytest.raises(AttributeError):
        trade.price.amount = trade.price.amount
    with pytest.raises(AttributeError):
        trade.participant_reference.participant_identity = ParticipantIdentity(
            "participant-opaque-002"
        )


def test_trade_does_not_support_ordering():
    with pytest.raises(TypeError):
        _ = _build_trade() < _build_trade(trade_identity=_build_trade_identity("trade-opaque-002"))


def test_historical_identity_remains_stable_after_attempted_mutation():
    trade = _build_trade()
    identity = trade.trade_identity

    with pytest.raises(AttributeError):
        trade.trade_identity = _build_trade_identity("trade-opaque-002")

    assert trade.trade_identity is identity


def test_aggregate_boundary_remains_intact():
    trade = _build_trade()

    assert trade.trade_identity is not None
    assert trade.listing is not None
    assert trade.point_in_time is not None
    assert trade.quantity is not None
    assert trade.price is not None
    assert trade.participant_reference is not None
