"""Tests for Northstar's record of one futures order meant for a broker."""

from __future__ import annotations

from dataclasses import fields

import pytest

from northstar_core.broker_execution import (
    BrokerAccountReference,
    BrokerEnvironment,
    BrokerOrderId,
    BrokerOrderStatus,
    ClientOrderIdentity,
    FuturesBrokerExecutionIntent,
    FuturesBrokerOrder,
    InvalidFuturesBrokerOrderError,
)
from northstar_core.derivatives import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, PointInTime, Symbol
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.paper_trading import (
    FuturesContractCount,
    FuturesExecutionIntent,
    FuturesPaperOrder,
    OrderSide,
    PaperOrderIdentity,
    PaperPortfolioIdentity,
)
from northstar_core.strategy import StrategyIdentity

_CONTRACT = FuturesContract(
    FuturesProductReference(Symbol("ES"), ExchangeCode("CME")), ExpirationDate("2026-12-18")
)
_STRATEGY = StrategyIdentity("alpha")
_DECIDED_AT = PointInTime("2026-09-24T21:00:00Z")
_INTENT = FuturesBrokerExecutionIntent(
    BrokerAccountReference("broker-a", "DU123", BrokerEnvironment.DEMO),
    _CONTRACT,
    OrderSide.BUY,
    FuturesContractCount(1),
    _STRATEGY,
    _DECIDED_AT,
)


def _order(**overrides: object) -> FuturesBrokerOrder:
    values: dict[str, object] = {"identity": ClientOrderIdentity("client-1"), "intent": _INTENT}
    values.update(overrides)
    return FuturesBrokerOrder(**values)


def test_order_preserves_every_member() -> None:
    order = _order()

    assert order.identity == ClientOrderIdentity("client-1")
    assert order.intent is _INTENT


def test_the_order_carries_no_broker_fact() -> None:
    """Broker identifiers, statuses and executions are later observations."""
    assert [field.name for field in fields(FuturesBrokerOrder)] == ["identity", "intent"]
    for name in ("status", "broker_order_id", "executions", "filled_contracts"):
        assert name not in FuturesBrokerOrder.__slots__
        assert not hasattr(_order(), name)


def test_a_status_cannot_be_supplied() -> None:
    with pytest.raises(TypeError):
        FuturesBrokerOrder(ClientOrderIdentity("client-1"), _INTENT, BrokerOrderStatus.WORKING)


@pytest.mark.parametrize(
    ("field", "message"),
    [("identity", "identity cannot be None"), ("intent", "intent cannot be None")],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidFuturesBrokerOrderError, match=message):
        _order(**{field: None})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("identity", "client-1", "must be a ClientOrderIdentity"),
        ("identity", BrokerOrderId("client-1"), "must be a ClientOrderIdentity"),
        ("identity", PaperOrderIdentity("client-1"), "must be a ClientOrderIdentity"),
        ("intent", "intent", "must be a FuturesBrokerExecutionIntent"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidFuturesBrokerOrderError, match=message):
        _order(**{field: value})


def test_a_paper_intent_is_rejected() -> None:
    paper = FuturesExecutionIntent(
        PaperPortfolioIdentity("paper-1"),
        _CONTRACT,
        OrderSide.BUY,
        FuturesContractCount(1),
        _STRATEGY,
        _DECIDED_AT,
    )

    with pytest.raises(InvalidFuturesBrokerOrderError, match="FuturesBrokerExecutionIntent"):
        _order(intent=paper)


def test_a_broker_intent_cannot_become_a_paper_order() -> None:
    """The boundary holds in both directions, enforced by the paper value itself."""
    with pytest.raises(ValidationError, match="FuturesExecutionIntent"):
        FuturesPaperOrder(PaperOrderIdentity("order-1"), _INTENT)  # type: ignore[arg-type]


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesBrokerOrderError, ValidationError)


def test_order_is_immutable() -> None:
    order = _order()

    with pytest.raises(AttributeError):
        order.identity = ClientOrderIdentity("client-2")  # type: ignore[misc]


def test_equivalent_orders_compare_and_hash_equal() -> None:
    assert _order() == _order()
    assert hash(_order()) == hash(_order())
    assert _order() != _order(identity=ClientOrderIdentity("client-2"))


def test_string_and_repr_forms() -> None:
    order = _order()

    assert str(order) == f"client-1 {_INTENT}"
    assert repr(order) == (
        f"FuturesBrokerOrder(identity=ClientOrderIdentity(identity='client-1'), intent={_INTENT!r})"
    )
