"""Tests for the simulated futures order awaiting its fill."""

from __future__ import annotations

from dataclasses import fields
from typing import get_type_hints

import pytest

from northstar_core.derivatives import ExpirationDate
from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    ExchangeCode,
    PointInTime,
    Quantity,
    Symbol,
)
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.paper_trading import (
    ExecutionIntent,
    FuturesContractCount,
    FuturesExecutionIntent,
    FuturesPaperOrder,
    InvalidFuturesPaperOrderError,
    OrderSide,
    PaperFillIdentity,
    PaperOrderIdentity,
    PaperOrderStatus,
    PaperPortfolioIdentity,
)
from northstar_core.strategy import StrategyIdentity

_PORTFOLIO = PaperPortfolioIdentity("paper-1")
_CONTRACT = FuturesContract(
    FuturesProductReference(Symbol("ES"), ExchangeCode("CME")), ExpirationDate("2026-03-20")
)
_STRATEGY = StrategyIdentity("alpha")
_DECIDED_AT = PointInTime("2026-01-20T22:00:00Z")
_INTENT = FuturesExecutionIntent(
    _PORTFOLIO, _CONTRACT, OrderSide.BUY, FuturesContractCount(1), _STRATEGY, _DECIDED_AT
)


def _order(**overrides: object) -> FuturesPaperOrder:
    values: dict[str, object] = {"identity": PaperOrderIdentity("order-1"), "intent": _INTENT}
    values.update(overrides)
    return FuturesPaperOrder(**values)


def test_order_preserves_every_member() -> None:
    order = _order()

    assert order.identity == PaperOrderIdentity("order-1")
    assert order.intent is _INTENT


def test_a_sell_order_is_constructible() -> None:
    intent = FuturesExecutionIntent(
        _PORTFOLIO, _CONTRACT, OrderSide.SELL, FuturesContractCount(3), _STRATEGY, _DECIDED_AT
    )

    assert _order(intent=intent).intent.side is OrderSide.SELL


def test_the_order_has_no_status_field() -> None:
    """An order exists before its fill bar; it must not claim a terminal result."""
    assert [field.name for field in fields(FuturesPaperOrder)] == ["identity", "intent"]
    assert "status" not in FuturesPaperOrder.__slots__
    assert not hasattr(_order(), "status")


def test_paper_order_status_is_not_part_of_the_value() -> None:
    hints = get_type_hints(FuturesPaperOrder)

    assert PaperOrderStatus not in hints.values()


def test_a_status_cannot_be_supplied() -> None:
    with pytest.raises(TypeError):
        FuturesPaperOrder(PaperOrderIdentity("order-1"), _INTENT, PaperOrderStatus.FILLED)


@pytest.mark.parametrize(
    ("field", "message"),
    [("identity", "identity cannot be None"), ("intent", "intent cannot be None")],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidFuturesPaperOrderError, match=message):
        _order(**{field: None})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("identity", "order-1", "must be a PaperOrderIdentity"),
        ("identity", PaperFillIdentity("order-1"), "must be a PaperOrderIdentity"),
        ("intent", "intent", "must be a FuturesExecutionIntent"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidFuturesPaperOrderError, match=message):
        _order(**{field: value})


def test_an_equity_intent_is_rejected() -> None:
    equity = ExecutionIntent(
        _PORTFOLIO,
        ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ")),
        OrderSide.BUY,
        Quantity("1"),
        _STRATEGY,
        _DECIDED_AT,
    )

    with pytest.raises(InvalidFuturesPaperOrderError, match="must be a FuturesExecutionIntent"):
        _order(intent=equity)


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesPaperOrderError, ValidationError)


def test_order_is_immutable() -> None:
    order = _order()

    with pytest.raises(AttributeError):
        order.identity = PaperOrderIdentity("order-2")  # type: ignore[misc]


def test_equivalent_orders_compare_and_hash_equal() -> None:
    assert _order() == _order()
    assert hash(_order()) == hash(_order())
    assert _order() != _order(identity=PaperOrderIdentity("order-2"))
