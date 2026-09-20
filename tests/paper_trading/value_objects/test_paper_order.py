"""Tests for the terminal record of one simulated execution attempt."""

from __future__ import annotations

import pytest

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    ExchangeCode,
    PointInTime,
    Quantity,
    Symbol,
)
from northstar_core.paper_trading import (
    ExecutionIntent,
    InvalidPaperOrderError,
    OrderSide,
    PaperOrder,
    PaperOrderIdentity,
    PaperOrderStatus,
    PaperPortfolioIdentity,
)
from northstar_core.strategy import StrategyIdentity

_IDENTITY = PaperOrderIdentity("order-1")
_INTENT = ExecutionIntent(
    PaperPortfolioIdentity("paper-1"),
    ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ")),
    OrderSide.BUY,
    Quantity("10"),
    StrategyIdentity("alpha"),
    PointInTime("2026-01-20T16:00:00Z"),
)


def _order(**overrides: object) -> PaperOrder:
    values: dict[str, object] = {
        "identity": _IDENTITY,
        "intent": _INTENT,
        "status": PaperOrderStatus.FILLED,
    }
    values.update(overrides)
    return PaperOrder(**values)


def test_order_preserves_every_member() -> None:
    order = _order()

    assert order.identity == _IDENTITY
    assert order.intent == _INTENT
    assert order.status is PaperOrderStatus.FILLED


def test_both_terminal_results_are_constructible() -> None:
    assert _order(status=PaperOrderStatus.FILLED).status is PaperOrderStatus.FILLED
    assert _order(status=PaperOrderStatus.REJECTED).status is PaperOrderStatus.REJECTED


def test_intent_detail_is_not_duplicated_as_order_state() -> None:
    """Listing, side, quantity and strategy stay owned by the frozen intent."""
    order = _order()

    for duplicated in ("listing_reference", "side", "quantity", "strategy_identity"):
        assert not hasattr(order, duplicated)
    assert order.intent.listing_reference == _INTENT.listing_reference
    assert order.intent.side is OrderSide.BUY


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("identity", "identity cannot be None"),
        ("intent", "intent cannot be None"),
        ("status", "status cannot be None"),
    ],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidPaperOrderError, match=message):
        _order(**{field: None})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("identity", "order-1", "must be a PaperOrderIdentity"),
        ("intent", "intent", "must be an ExecutionIntent"),
        ("status", "FILLED", "must be a PaperOrderStatus"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidPaperOrderError, match=message):
        _order(**{field: value})


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidPaperOrderError, ValidationError)
    with pytest.raises(ValidationError):
        _order(status=None)


def test_order_is_immutable() -> None:
    order = _order()

    with pytest.raises(AttributeError):
        order.status = PaperOrderStatus.REJECTED
    with pytest.raises(AttributeError):
        order.identity = PaperOrderIdentity("order-2")


def test_order_exposes_no_lifecycle_behaviour() -> None:
    """A paper order is created already resolved; nothing advances or withdraws it."""
    order = _order()

    for method in ("fill", "cancel", "replace", "amend", "submit", "reject", "transition"):
        assert not hasattr(order, method)


def test_equivalent_orders_compare_and_hash_equal() -> None:
    assert _order() == _order()
    assert hash(_order()) == hash(_order())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("identity", PaperOrderIdentity("order-2")),
        ("status", PaperOrderStatus.REJECTED),
    ],
)
def test_orders_differing_in_any_member_are_not_equal(field: str, value: object) -> None:
    assert _order() != _order(**{field: value})


def test_orders_differing_only_by_intent_are_not_equal() -> None:
    other = ExecutionIntent(
        _INTENT.portfolio_identity,
        _INTENT.listing_reference,
        OrderSide.SELL,
        _INTENT.quantity,
        _INTENT.strategy_identity,
        _INTENT.decided_at,
    )

    assert _order() != _order(intent=other)


def test_order_is_usable_as_a_dictionary_key() -> None:
    assert {_order(): "kept"}[_order()] == "kept"


def test_string_and_repr_forms_expose_the_result() -> None:
    order = _order()

    assert str(order).startswith("order-1 FILLED BUY 10 AAPL@NASDAQ")
    assert repr(order).startswith("PaperOrder(identity=")
