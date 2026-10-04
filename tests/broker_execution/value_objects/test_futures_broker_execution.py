"""Tests for one broker-reported execution against a Northstar futures order."""

from __future__ import annotations

from dataclasses import fields
from decimal import Decimal

import pytest

from northstar_core.broker_execution import (
    BrokerAccountReference,
    BrokerEnvironment,
    BrokerExecutionId,
    BrokerOrderId,
    ClientOrderIdentity,
    FuturesBrokerExecution,
    FuturesBrokerExecutionIntent,
    FuturesBrokerOrder,
    InvalidFuturesBrokerExecutionError,
)
from northstar_core.derivatives import ExpirationDate, QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    Currency,
    ExchangeCode,
    PointInTime,
    Price,
    Symbol,
)
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.paper_trading import (
    FuturesContractCount,
    FuturesPaperFill,
    OrderSide,
    PaperOrderIdentity,
)
from northstar_core.strategy import StrategyIdentity

_ACCOUNT = BrokerAccountReference("broker-a", "DU123", BrokerEnvironment.DEMO)
_CONTRACT = FuturesContract(
    FuturesProductReference(Symbol("ES"), ExchangeCode("CME")), ExpirationDate("2026-12-18")
)
_DECIDED_AT = PointInTime("2026-09-24T21:00:00Z")
_ORDER = FuturesBrokerOrder(
    ClientOrderIdentity("client-1"),
    FuturesBrokerExecutionIntent(
        _ACCOUNT,
        _CONTRACT,
        OrderSide.SELL,
        FuturesContractCount(2),
        StrategyIdentity("alpha"),
        _DECIDED_AT,
    ),
)
_EXECUTED_AT = PointInTime("2026-09-24T23:45:01.25Z")


def _execution(**overrides: object) -> FuturesBrokerExecution:
    values: dict[str, object] = {
        "identity": BrokerExecutionId("E-1"),
        "order": _ORDER,
        "broker_order_id": BrokerOrderId("B-1"),
        "contracts": FuturesContractCount(2),
        "price": QuoteValue(Decimal("5432.25")),
        "executed_at": _EXECUTED_AT,
    }
    values.update(overrides)
    return FuturesBrokerExecution(**values)


def test_execution_preserves_every_member() -> None:
    execution = _execution()

    assert execution.identity == BrokerExecutionId("E-1")
    assert execution.order is _ORDER
    assert execution.broker_order_id == BrokerOrderId("B-1")
    assert execution.contracts == FuturesContractCount(2)
    assert execution.price == QuoteValue(Decimal("5432.25"))
    assert execution.executed_at is _EXECUTED_AT


def test_the_field_shape_is_exactly_the_approved_contract() -> None:
    assert [field.name for field in fields(FuturesBrokerExecution)] == [
        "identity",
        "order",
        "broker_order_id",
        "contracts",
        "price",
        "executed_at",
    ]


def test_account_contract_and_side_are_derived_not_stored() -> None:
    execution = _execution()

    assert execution.account is _ACCOUNT
    assert execution.contract is _CONTRACT
    assert execution.side is OrderSide.SELL
    for name in ("account", "contract", "side"):
        assert name not in FuturesBrokerExecution.__slots__


# -- quantity ---------------------------------------------------------------------


def test_a_partial_execution_is_valid() -> None:
    assert _execution(contracts=FuturesContractCount(1)).contracts == FuturesContractCount(1)


def test_a_complete_execution_is_valid() -> None:
    assert _execution(contracts=FuturesContractCount(2)).contracts == FuturesContractCount(2)


@pytest.mark.parametrize("count", [3, 10])
def test_contracts_cannot_exceed_the_order(count: int) -> None:
    with pytest.raises(InvalidFuturesBrokerExecutionError, match="cannot exceed"):
        _execution(contracts=FuturesContractCount(count))


# -- price ------------------------------------------------------------------------


@pytest.mark.parametrize("price", ["0", "-37.63", "118.515625"])
def test_zero_negative_and_fine_quotes_are_valid(price: str) -> None:
    assert _execution(price=QuoteValue(Decimal(price))).price == QuoteValue(Decimal(price))


# -- timing -----------------------------------------------------------------------


def test_execution_strictly_after_the_decision_is_valid() -> None:
    later = PointInTime("2026-09-24T21:00:00.000001Z")

    assert _execution(executed_at=later).executed_at is later


@pytest.mark.parametrize(
    "instant",
    [
        "2026-09-24T21:00:00Z",
        "2026-09-24T16:00:00-05:00",  # the same instant spelled with an offset
        "2026-09-24T20:59:59.999999Z",
        "2026-09-23T23:45:00Z",
    ],
)
def test_execution_at_or_before_the_decision_is_rejected(instant: str) -> None:
    with pytest.raises(InvalidFuturesBrokerExecutionError, match="strictly after"):
        _execution(executed_at=PointInTime(instant))


def test_ordering_is_chronological_not_textual() -> None:
    """``...21:00:00.5Z`` sorts before ``...21:00:00Z`` as text but is later."""
    later = PointInTime("2026-09-24T21:00:00.5Z")

    assert later.value < _DECIDED_AT.value
    assert _execution(executed_at=later).executed_at is later


# -- member types -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("identity", "identity cannot be None"),
        ("order", "order cannot be None"),
        ("broker_order_id", "broker order id cannot be None"),
        ("contracts", "contracts cannot be None"),
        ("price", "price cannot be None"),
        ("executed_at", "execution instant cannot be None"),
    ],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidFuturesBrokerExecutionError, match=message):
        _execution(**{field: None})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("identity", "E-1", "must be a BrokerExecutionId"),
        ("identity", BrokerOrderId("E-1"), "must be a BrokerExecutionId"),
        ("order", ClientOrderIdentity("client-1"), "must be a FuturesBrokerOrder"),
        ("broker_order_id", "B-1", "must be a BrokerOrderId"),
        ("broker_order_id", BrokerExecutionId("B-1"), "must be a BrokerOrderId"),
        ("contracts", 2, "must be a FuturesContractCount"),
        ("price", Decimal("5432.25"), "must be a QuoteValue"),
        ("price", Price(Decimal("5432.25"), Currency("USD")), "must be a QuoteValue"),
        ("executed_at", "2026-09-24T23:45:01Z", "must be a PointInTime"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidFuturesBrokerExecutionError, match=message):
        _execution(**{field: value})


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesBrokerExecutionError, ValidationError)


def test_a_broker_execution_is_not_a_simulated_fill() -> None:
    assert not issubclass(FuturesBrokerExecution, FuturesPaperFill)
    assert not issubclass(FuturesPaperFill, FuturesBrokerExecution)
    with pytest.raises(ValidationError):
        _execution(order=PaperOrderIdentity("order-1"))


# -- equality and representation -------------------------------------------------


def test_execution_is_immutable() -> None:
    execution = _execution()

    with pytest.raises(AttributeError):
        execution.price = QuoteValue(Decimal("1"))  # type: ignore[misc]


def test_equivalent_executions_compare_and_hash_equal() -> None:
    assert _execution() == _execution(price=QuoteValue(Decimal("5432.250")))
    assert hash(_execution()) == hash(_execution())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("identity", BrokerExecutionId("E-2")),
        ("broker_order_id", BrokerOrderId("B-2")),
        ("contracts", FuturesContractCount(1)),
        ("price", QuoteValue(Decimal("5432.5"))),
        ("executed_at", PointInTime("2026-09-24T23:45:02Z")),
    ],
)
def test_executions_differing_in_any_member_are_not_equal(field: str, value: object) -> None:
    assert _execution() != _execution(**{field: value})


def test_string_and_repr_forms() -> None:
    execution = _execution()

    assert str(execution) == (
        "E-1 client-1 B-1 SELL 2 ES@CME 2026-12-18 @ 5432.25 2026-09-24T23:45:01.25Z"
    )
    assert repr(execution).startswith(
        "FuturesBrokerExecution(identity=BrokerExecutionId(identity='E-1'), "
    )
