"""Reference contract test suite for the Order aggregate root.

This suite defines the Northstar Reference Aggregate Contract for Order.
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
from northstar_core.orders import InvalidOrderError, Order, OrderIdentity, OrderStatus


def _build_listing(symbol: str = "AAPL") -> Listing:
    instrument = Instrument(Symbol(symbol), "Apple Inc.", "Equity")
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")
    return Listing(
        instrument,
        exchange,
        Currency("USD"),
        ListingStatus("Active"),
        Tradability("Permitted"),
    )


def _build_point_in_time(value: str = "2026-08-17T09:30:00Z") -> PointInTime:
    return PointInTime(value)


def _build_order_identity(value: str = "order-opaque-001") -> OrderIdentity:
    return OrderIdentity(value)


def _build_quantity(value: str = "10") -> Quantity:
    return Quantity(value)


def _build_price(value: str = "100") -> Price:
    return Price(value, Currency("USD"))


def _build_participant_reference(value: str = "participant-opaque-001") -> ParticipantReference:
    return ParticipantReference(ParticipantIdentity(value))


def _build_order_status(value: str = "Submitted") -> OrderStatus:
    return OrderStatus(value)


def _build_order(
    *,
    order_identity: OrderIdentity | None = None,
    listing: Listing | None = None,
    point_in_time: PointInTime | None = None,
    quantity: Quantity | None = None,
    price: Price | None = None,
    participant_reference: ParticipantReference | None = None,
    order_status: OrderStatus | None = None,
) -> Order:
    return Order(
        order_identity or _build_order_identity(),
        listing or _build_listing(),
        point_in_time or _build_point_in_time(),
        quantity or _build_quantity(),
        price or _build_price(),
        participant_reference or _build_participant_reference(),
        order_status or _build_order_status(),
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_order_from_approved_aggregate_composition():
    order = _build_order()

    assert isinstance(order, Order)


def test_construction_preserves_approved_aggregate_composition():
    order_identity = _build_order_identity()
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    quantity = _build_quantity()
    price = _build_price()
    participant_reference = _build_participant_reference()
    order_status = _build_order_status()

    order = Order(
        order_identity,
        listing,
        point_in_time,
        quantity,
        price,
        participant_reference,
        order_status,
    )

    assert order.order_identity is order_identity
    assert order.listing is listing
    assert order.point_in_time is point_in_time
    assert order.quantity is quantity
    assert order.price is price
    assert order.participant_reference is participant_reference
    assert order.order_status is order_status


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none_order_identity():
    with pytest.raises(InvalidOrderError, match="identity cannot be None"):
        Order(
            None,
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
            _build_order_status(),
        )


def test_rejects_none_listing():
    with pytest.raises(InvalidOrderError, match="listing cannot be None"):
        Order(
            _build_order_identity(),
            None,
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
            _build_order_status(),
        )


def test_rejects_none_point_in_time():
    with pytest.raises(InvalidOrderError, match="point-in-time context cannot be None"):
        Order(
            _build_order_identity(),
            _build_listing(),
            None,
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
            _build_order_status(),
        )


def test_rejects_none_quantity():
    with pytest.raises(InvalidOrderError, match="quantity cannot be None"):
        Order(
            _build_order_identity(),
            _build_listing(),
            _build_point_in_time(),
            None,
            _build_price(),
            _build_participant_reference(),
            _build_order_status(),
        )


def test_rejects_none_price():
    with pytest.raises(InvalidOrderError, match="price cannot be None"):
        Order(
            _build_order_identity(),
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            None,
            _build_participant_reference(),
            _build_order_status(),
        )


def test_rejects_none_participant_reference():
    with pytest.raises(InvalidOrderError, match="participant reference cannot be None"):
        Order(
            _build_order_identity(),
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            None,
            _build_order_status(),
        )


def test_rejects_none_order_status():
    with pytest.raises(InvalidOrderError, match="status cannot be None"):
        Order(
            _build_order_identity(),
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
            None,
        )


def test_rejects_invalid_order_identity_type():
    with pytest.raises(InvalidOrderError, match="identity must be an OrderIdentity"):
        Order(
            "identity",
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
            _build_order_status(),
        )


def test_rejects_invalid_listing_type():
    with pytest.raises(InvalidOrderError, match="listing must be a Listing"):
        Order(
            _build_order_identity(),
            "listing",
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
            _build_order_status(),
        )


def test_rejects_invalid_point_in_time_type():
    with pytest.raises(InvalidOrderError, match="point-in-time context must be a PointInTime"):
        Order(
            _build_order_identity(),
            _build_listing(),
            "time",
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
            _build_order_status(),
        )


def test_rejects_invalid_quantity_type():
    with pytest.raises(InvalidOrderError, match="quantity must be a Quantity"):
        Order(
            _build_order_identity(),
            _build_listing(),
            _build_point_in_time(),
            "10",
            _build_price(),
            _build_participant_reference(),
            _build_order_status(),
        )


def test_rejects_invalid_price_type():
    with pytest.raises(InvalidOrderError, match="price must be a Price"):
        Order(
            _build_order_identity(),
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            "100 USD",
            _build_participant_reference(),
            _build_order_status(),
        )


def test_rejects_invalid_participant_reference_type():
    with pytest.raises(
        InvalidOrderError, match="participant reference must be a ParticipantReference"
    ):
        Order(
            _build_order_identity(),
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            "participant",
            _build_order_status(),
        )


def test_rejects_invalid_order_status_type():
    with pytest.raises(InvalidOrderError, match="status must be an OrderStatus"):
        Order(
            _build_order_identity(),
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
            "Submitted",
        )


def test_invalid_order_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Order(
            None,
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
            _build_order_status(),
        )


def test_invalid_order_error_is_a_value_error():
    with pytest.raises(ValueError):
        Order(
            None,
            _build_listing(),
            _build_point_in_time(),
            _build_quantity(),
            _build_price(),
            _build_participant_reference(),
            _build_order_status(),
        )


# ---------------------------------------------------------------------------
# Aggregate Composition
# ---------------------------------------------------------------------------


def test_order_composes_exactly_the_approved_dependencies():
    order = _build_order()

    assert isinstance(order.order_identity, OrderIdentity)
    assert isinstance(order.listing, Listing)
    assert isinstance(order.point_in_time, PointInTime)
    assert isinstance(order.quantity, Quantity)
    assert isinstance(order.price, Price)
    assert isinstance(order.participant_reference, ParticipantReference)
    assert isinstance(order.order_status, OrderStatus)


def test_order_does_not_compose_participant_trade_portfolio_or_market_data():
    order = _build_order()

    assert not hasattr(order, "participant")
    assert not hasattr(order, "trade")
    assert not hasattr(order, "portfolio")
    assert not hasattr(order, "quote")
    assert not hasattr(order, "tick")
    assert not hasattr(order, "ohlc_bar")
    assert not hasattr(order, "order_book")


def test_composed_concepts_remain_authoritative_owners_of_business_meaning():
    order = _build_order()

    assert order.order_identity.identity == "order-opaque-001"
    assert order.participant_reference.participant_identity.identity == ("participant-opaque-001")
    assert order.order_status.lifecycle_meaning == "Submitted"


# ---------------------------------------------------------------------------
# Identity Semantics
# ---------------------------------------------------------------------------


def test_orders_with_same_identity_compare_equal_despite_different_composition():
    identity = _build_order_identity()

    left = _build_order(
        order_identity=identity,
        listing=_build_listing("AAPL"),
        point_in_time=_build_point_in_time("2026-08-17T09:30:00Z"),
        quantity=_build_quantity("10"),
        price=_build_price("100"),
        order_status=_build_order_status("Submitted"),
    )
    right = _build_order(
        order_identity=_build_order_identity(" order-opaque-001 "),
        listing=_build_listing("MSFT"),
        point_in_time=_build_point_in_time("2026-08-17T14:30:00+05:00"),
        quantity=_build_quantity("25"),
        price=_build_price("200"),
        order_status=_build_order_status("Accepted"),
    )

    assert left == right


def test_orders_with_different_identity_do_not_compare_equal():
    left = _build_order(order_identity=_build_order_identity("order-opaque-001"))
    right = _build_order(order_identity=_build_order_identity("order-opaque-002"))

    assert left != right


def test_order_equality_is_based_only_on_order_identity():
    identity = _build_order_identity("order-opaque-001")
    left = _build_order(order_identity=identity)
    right = _build_order(
        order_identity=_build_order_identity("order-opaque-001"),
        listing=_build_listing("GOOG"),
    )

    assert left == right


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_orders_have_equal_hashes_from_order_identity():
    left = _build_order(order_identity=_build_order_identity("order-opaque-001"))
    right = _build_order(order_identity=_build_order_identity(" order-opaque-001 "))

    assert hash(left) == hash(right)


def test_order_is_usable_as_dictionary_key():
    key = _build_order(order_identity=_build_order_identity("order-opaque-001"))
    index = {key: "aggregate"}
    probe = _build_order(order_identity=_build_order_identity("order-opaque-001"))

    assert index[probe] == "aggregate"


def test_order_hashing_follows_order_identity():
    order = _build_order(order_identity=_build_order_identity("order-opaque-001"))

    assert hash(order) == hash(order.order_identity)


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_repr_contains_order_and_approved_composed_components():
    representation = repr(_build_order())

    assert "Order(" in representation
    assert "OrderIdentity(" in representation
    assert "Listing(" in representation
    assert "ParticipantReference(" in representation
    assert "OrderStatus(" in representation


def test_str_returns_deterministic_business_representation():
    order = _build_order()

    assert str(order) == str(_build_order())
    assert "order-opaque-001" in str(order)
    assert "AAPL@NASDAQ" in str(order)


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_order_aggregate_structure_is_mutable():
    order = _build_order()
    replacement_status = _build_order_status("Accepted")

    order.order_status = replacement_status

    assert order.order_status is replacement_status


def test_composed_value_objects_remain_immutable():
    order = _build_order()

    with pytest.raises(AttributeError):
        order.order_identity.identity = "order-opaque-002"
    with pytest.raises(AttributeError):
        order.quantity.value = order.quantity.value
    with pytest.raises(AttributeError):
        order.price.amount = order.price.amount
    with pytest.raises(AttributeError):
        order.participant_reference.participant_identity = ParticipantIdentity(
            "participant-opaque-002"
        )
    with pytest.raises(AttributeError):
        order.order_status.lifecycle_meaning = "Accepted"


def test_order_does_not_support_ordering():
    left = _build_order(order_identity=_build_order_identity("order-opaque-001"))
    right = _build_order(order_identity=_build_order_identity("order-opaque-002"))

    with pytest.raises(TypeError):
        _ = left < right


def test_lifecycle_change_preserves_order_identity_and_equality():
    identity = _build_order_identity("order-opaque-001")
    order = _build_order(order_identity=identity)
    equivalent = _build_order(order_identity=_build_order_identity("order-opaque-001"))

    order.order_status = _build_order_status("Accepted")

    assert order.order_identity is identity
    assert order == equivalent


def test_aggregate_ownership_remains_intact():
    order = _build_order()

    assert order.order_identity is not None
    assert order.listing is not None
    assert order.point_in_time is not None
    assert order.quantity is not None
    assert order.price is not None
    assert order.participant_reference is not None
    assert order.order_status is not None
