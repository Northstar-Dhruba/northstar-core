"""Tests for the approved intent to execute one futures trade through a broker."""

from __future__ import annotations

from dataclasses import fields

import pytest

from northstar_core.broker_execution import (
    BrokerAccountReference,
    BrokerEnvironment,
    FuturesBrokerExecutionIntent,
    InvalidFuturesBrokerExecutionIntentError,
)
from northstar_core.derivatives import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, PointInTime, Symbol
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.paper_trading import (
    FuturesContractCount,
    FuturesExecutionIntent,
    OrderSide,
    PaperPortfolioIdentity,
)
from northstar_core.strategy import StrategyIdentity

_ACCOUNT = BrokerAccountReference("broker-a", "DU123", BrokerEnvironment.DEMO)
_CONTRACT = FuturesContract(
    FuturesProductReference(Symbol("ES"), ExchangeCode("CME")), ExpirationDate("2026-12-18")
)
_STRATEGY = StrategyIdentity("alpha")
_DECIDED_AT = PointInTime("2026-09-24T21:00:00Z")


def _intent(**overrides: object) -> FuturesBrokerExecutionIntent:
    values: dict[str, object] = {
        "account": _ACCOUNT,
        "contract": _CONTRACT,
        "side": OrderSide.BUY,
        "contracts": FuturesContractCount(1),
        "strategy_identity": _STRATEGY,
        "decided_at": _DECIDED_AT,
    }
    values.update(overrides)
    return FuturesBrokerExecutionIntent(**values)


def test_intent_preserves_every_member() -> None:
    intent = _intent()

    assert intent.account is _ACCOUNT
    assert intent.contract is _CONTRACT
    assert intent.side is OrderSide.BUY
    assert intent.contracts == FuturesContractCount(1)
    assert intent.strategy_identity is _STRATEGY
    assert intent.decided_at is _DECIDED_AT


@pytest.mark.parametrize("side", [OrderSide.BUY, OrderSide.SELL])
def test_buy_and_sell_are_constructible(side: OrderSide) -> None:
    assert _intent(side=side).side is side


def test_the_field_shape_is_exactly_the_approved_contract() -> None:
    assert [field.name for field in fields(FuturesBrokerExecutionIntent)] == [
        "account",
        "contract",
        "side",
        "contracts",
        "strategy_identity",
        "decided_at",
    ]


def test_the_broker_intent_is_not_the_paper_intent() -> None:
    """Paper and broker execution must not be able to cross boundaries."""
    paper = FuturesExecutionIntent(
        PaperPortfolioIdentity("paper-1"),
        _CONTRACT,
        OrderSide.BUY,
        FuturesContractCount(1),
        _STRATEGY,
        _DECIDED_AT,
    )

    assert not issubclass(FuturesBrokerExecutionIntent, FuturesExecutionIntent)
    assert not issubclass(FuturesExecutionIntent, FuturesBrokerExecutionIntent)
    assert _intent() != paper


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("account", "account cannot be None"),
        ("contract", "contract cannot be None"),
        ("side", "side cannot be None"),
        ("contracts", "contracts cannot be None"),
        ("strategy_identity", "strategy identity cannot be None"),
        ("decided_at", "decision instant cannot be None"),
    ],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidFuturesBrokerExecutionIntentError, match=message):
        _intent(**{field: None})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("account", PaperPortfolioIdentity("paper-1"), "must be a BrokerAccountReference"),
        ("account", "DU123", "must be a BrokerAccountReference"),
        ("contract", "ES", "must be a FuturesContract"),
        ("side", "BUY", "must be an OrderSide"),
        ("contracts", 1, "must be a FuturesContractCount"),
        ("strategy_identity", "alpha", "must be a StrategyIdentity"),
        ("decided_at", "2026-09-24T21:00:00Z", "must be a PointInTime"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidFuturesBrokerExecutionIntentError, match=message):
        _intent(**{field: value})


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesBrokerExecutionIntentError, ValidationError)


def test_intent_is_immutable() -> None:
    intent = _intent()

    with pytest.raises(AttributeError):
        intent.side = OrderSide.SELL  # type: ignore[misc]


def test_equivalent_intents_compare_and_hash_equal() -> None:
    assert _intent() == _intent()
    assert hash(_intent()) == hash(_intent())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("account", BrokerAccountReference("broker-a", "DU999", BrokerEnvironment.DEMO)),
        (
            "contract",
            FuturesContract(
                FuturesProductReference(Symbol("ES"), ExchangeCode("CME")),
                ExpirationDate("2027-03-19"),
            ),
        ),
        ("side", OrderSide.SELL),
        ("contracts", FuturesContractCount(2)),
        ("strategy_identity", StrategyIdentity("beta")),
        ("decided_at", PointInTime("2026-09-25T21:00:00Z")),
    ],
)
def test_intents_differing_in_any_member_are_not_equal(field: str, value: object) -> None:
    assert _intent() != _intent(**{field: value})


def test_offset_equivalent_decision_instants_are_the_same_intent() -> None:
    assert _intent() == _intent(decided_at=PointInTime("2026-09-24T16:00:00-05:00"))


def test_string_and_repr_forms() -> None:
    intent = _intent()

    assert str(intent) == ("BUY 1 ES@CME 2026-12-18 broker-a/DU123 DEMO alpha 2026-09-24T21:00:00Z")
    assert repr(intent).startswith(f"FuturesBrokerExecutionIntent(account={_ACCOUNT!r}, ")
