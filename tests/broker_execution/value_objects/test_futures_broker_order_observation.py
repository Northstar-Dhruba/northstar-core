"""Tests for the broker-reported state of one Northstar futures order."""

from __future__ import annotations

from dataclasses import fields

import pytest

from northstar_core.broker_execution import (
    BrokerAccountReference,
    BrokerEnvironment,
    BrokerExecutionId,
    BrokerOrderId,
    BrokerOrderStatus,
    ClientOrderIdentity,
    FuturesBrokerExecutionIntent,
    FuturesBrokerOrder,
    FuturesBrokerOrderObservation,
    InvalidFuturesBrokerOrderObservationError,
)
from northstar_core.derivatives import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, PointInTime, Symbol
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.paper_trading import FuturesContractCount, OrderSide
from northstar_core.strategy import StrategyIdentity

_REQUESTED = 3
_ORDER = FuturesBrokerOrder(
    ClientOrderIdentity("client-1"),
    FuturesBrokerExecutionIntent(
        BrokerAccountReference("broker-a", "DU123", BrokerEnvironment.DEMO),
        FuturesContract(
            FuturesProductReference(Symbol("ES"), ExchangeCode("CME")),
            ExpirationDate("2026-12-18"),
        ),
        OrderSide.SELL,
        FuturesContractCount(_REQUESTED),
        StrategyIdentity("alpha"),
        PointInTime("2026-09-24T21:00:00Z"),
    ),
)
_BROKER_ID = BrokerOrderId("B-1")
_OBSERVED_AT = PointInTime("2026-09-24T23:45:02Z")

W, F, C, R = (
    BrokerOrderStatus.WORKING,
    BrokerOrderStatus.FILLED,
    BrokerOrderStatus.CANCELLED,
    BrokerOrderStatus.REJECTED,
)


def _observation(**overrides: object) -> FuturesBrokerOrderObservation:
    values: dict[str, object] = {
        "order": _ORDER,
        "broker_order_id": _BROKER_ID,
        "status": W,
        "filled_contracts": 0,
        "observed_at": _OBSERVED_AT,
        "reason": None,
    }
    values.update(overrides)
    return FuturesBrokerOrderObservation(**values)


def test_observation_preserves_every_member() -> None:
    observation = _observation(status=C, filled_contracts=1, reason="expired at session end")

    assert observation.order is _ORDER
    assert observation.broker_order_id is _BROKER_ID
    assert observation.status is C
    assert observation.filled_contracts == 1
    assert observation.observed_at is _OBSERVED_AT
    assert observation.reason == "expired at session end"


def test_the_field_shape_carries_no_raw_payload() -> None:
    assert [field.name for field in fields(FuturesBrokerOrderObservation)] == [
        "order",
        "broker_order_id",
        "status",
        "filled_contracts",
        "observed_at",
        "reason",
    ]


# -- filled count and status ---------------------------------------------------


@pytest.mark.parametrize(
    ("status", "filled"),
    [
        (W, 0),  # acknowledged, nothing filled yet
        (W, 1),  # partial fill still working
        (W, _REQUESTED - 1),
        (F, _REQUESTED),
        (C, 0),
        (C, 2),  # partial fill then withdrawn
        (R, 0),
    ],
)
def test_consistent_fill_and_status_are_accepted(status: BrokerOrderStatus, filled: int) -> None:
    assert _observation(status=status, filled_contracts=filled).filled_contracts == filled


@pytest.mark.parametrize("status", [W, F, C, R])
def test_overfill_is_rejected(status: BrokerOrderStatus) -> None:
    with pytest.raises(InvalidFuturesBrokerOrderObservationError, match="cannot exceed"):
        _observation(status=status, filled_contracts=_REQUESTED + 1)


@pytest.mark.parametrize("filled", [0, 1, _REQUESTED - 1])
def test_filled_requires_a_complete_fill(filled: int) -> None:
    with pytest.raises(InvalidFuturesBrokerOrderObservationError, match="FILLED requires"):
        _observation(status=F, filled_contracts=filled)


@pytest.mark.parametrize("filled", [1, _REQUESTED])
def test_rejected_requires_nothing_filled(filled: int) -> None:
    with pytest.raises(InvalidFuturesBrokerOrderObservationError, match="REJECTED requires"):
        _observation(status=R, filled_contracts=filled)


@pytest.mark.parametrize("status", [W, C])
def test_working_and_cancelled_cannot_be_completely_filled(status: BrokerOrderStatus) -> None:
    with pytest.raises(InvalidFuturesBrokerOrderObservationError, match="complete fill is FILLED"):
        _observation(status=status, filled_contracts=_REQUESTED)


def test_negative_filled_count_is_rejected() -> None:
    with pytest.raises(InvalidFuturesBrokerOrderObservationError, match="cannot be negative"):
        _observation(filled_contracts=-1)


@pytest.mark.parametrize("value", [True, False])
def test_bool_filled_count_is_rejected(value: bool) -> None:
    with pytest.raises(InvalidFuturesBrokerOrderObservationError, match="must be an integer"):
        _observation(filled_contracts=value)


@pytest.mark.parametrize("value", [1.0, "1", FuturesContractCount(1), object()])
def test_non_integer_filled_count_is_rejected(value: object) -> None:
    with pytest.raises(InvalidFuturesBrokerOrderObservationError, match="must be an integer"):
        _observation(filled_contracts=value)


# -- broker order identifier -----------------------------------------------------


@pytest.mark.parametrize(("status", "filled"), [(W, 0), (W, 1), (F, _REQUESTED), (C, 0)])
def test_broker_order_id_is_required_unless_rejected(
    status: BrokerOrderStatus, filled: int
) -> None:
    with pytest.raises(InvalidFuturesBrokerOrderObservationError, match="is required unless"):
        _observation(broker_order_id=None, status=status, filled_contracts=filled)


def test_a_rejection_without_a_broker_order_id_is_valid() -> None:
    """A broker may refuse an order before assigning it an identifier."""
    observation = _observation(broker_order_id=None, status=R, reason="insufficient margin")

    assert observation.broker_order_id is None
    assert observation.status is R


def test_a_rejection_may_carry_a_broker_order_id() -> None:
    assert _observation(status=R).broker_order_id is _BROKER_ID


# -- reason -----------------------------------------------------------------------


def test_reason_is_optional() -> None:
    assert _observation().reason is None


def test_reason_surrounding_whitespace_is_normalized() -> None:
    assert _observation(reason="  outside trading hours \n").reason == "outside trading hours"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_blank_reason_is_rejected(value: str) -> None:
    with pytest.raises(InvalidFuturesBrokerOrderObservationError, match="reason cannot be empty"):
        _observation(reason=value)


@pytest.mark.parametrize("value", [1, True, b"reason", ["reason"]])
def test_non_string_reason_is_rejected(value: object) -> None:
    with pytest.raises(InvalidFuturesBrokerOrderObservationError, match="reason must be a string"):
        _observation(reason=value)


# -- member types -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("order", "order cannot be None"),
        ("status", "status cannot be None"),
        ("filled_contracts", "filled contracts cannot be None"),
        ("observed_at", "observation instant cannot be None"),
    ],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidFuturesBrokerOrderObservationError, match=message):
        _observation(**{field: None})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("order", ClientOrderIdentity("client-1"), "must be a FuturesBrokerOrder"),
        ("broker_order_id", "B-1", "must be a BrokerOrderId"),
        ("broker_order_id", BrokerExecutionId("B-1"), "must be a BrokerOrderId"),
        ("broker_order_id", ClientOrderIdentity("B-1"), "must be a BrokerOrderId"),
        ("status", "WORKING", "must be a BrokerOrderStatus"),
        ("observed_at", "2026-09-24T23:45:02Z", "must be a PointInTime"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidFuturesBrokerOrderObservationError, match=message):
        _observation(**{field: value})


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesBrokerOrderObservationError, ValidationError)


# -- derived, equality, representation ---------------------------------------------


def test_client_order_identity_is_derived_from_the_order() -> None:
    assert _observation().client_order_identity == ClientOrderIdentity("client-1")


@pytest.mark.parametrize(
    ("status", "filled", "terminal"),
    [(W, 1, False), (F, _REQUESTED, True), (C, 1, True), (R, 0, True)],
)
def test_is_terminal_follows_the_status(
    status: BrokerOrderStatus, filled: int, terminal: bool
) -> None:
    assert _observation(status=status, filled_contracts=filled).is_terminal is terminal


def test_observation_is_immutable() -> None:
    observation = _observation()

    with pytest.raises(AttributeError):
        observation.status = F  # type: ignore[misc]


def test_equivalent_observations_compare_and_hash_equal() -> None:
    assert _observation() == _observation(reason=None)
    assert hash(_observation(reason=" x ")) == hash(_observation(reason="x"))
    assert _observation() != _observation(filled_contracts=1)
    assert _observation() != _observation(observed_at=PointInTime("2026-09-24T23:45:03Z"))


def test_string_and_repr_forms() -> None:
    observation = _observation(filled_contracts=1)

    assert str(observation) == "client-1 B-1 WORKING 1/3 2026-09-24T23:45:02Z"
    assert repr(observation).startswith(f"FuturesBrokerOrderObservation(order={_ORDER!r}, ")
    assert repr(observation).endswith(
        "observed_at=PointInTime(value='2026-09-24T23:45:02Z'), reason=None)"
    )
