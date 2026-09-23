"""Tests for the approved intent to execute one simulated futures trade."""

from __future__ import annotations

from dataclasses import fields

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
    FuturesContractCount,
    FuturesExecutionIntent,
    InvalidFuturesExecutionIntentError,
    OrderSide,
    PaperPortfolioIdentity,
)
from northstar_core.strategy import StrategyIdentity

_PORTFOLIO = PaperPortfolioIdentity("paper-1")
_ES = FuturesProductReference(Symbol("ES"), ExchangeCode("CME"))
_CONTRACT = FuturesContract(_ES, ExpirationDate("2026-03-20"))
_STRATEGY = StrategyIdentity("alpha")
_DECIDED_AT = PointInTime("2026-01-20T22:00:00Z")


def _intent(**overrides: object) -> FuturesExecutionIntent:
    values: dict[str, object] = {
        "portfolio_identity": _PORTFOLIO,
        "contract": _CONTRACT,
        "side": OrderSide.BUY,
        "contracts": FuturesContractCount(2),
        "strategy_identity": _STRATEGY,
        "decided_at": _DECIDED_AT,
    }
    values.update(overrides)
    return FuturesExecutionIntent(**values)


def test_intent_preserves_every_member() -> None:
    intent = _intent()

    assert intent.portfolio_identity == _PORTFOLIO
    assert intent.contract == _CONTRACT
    assert intent.side is OrderSide.BUY
    assert intent.contracts == FuturesContractCount(2)
    assert intent.strategy_identity == _STRATEGY
    assert intent.decided_at == _DECIDED_AT


def test_buy_and_sell_are_constructible() -> None:
    assert _intent(side=OrderSide.BUY).side is OrderSide.BUY
    assert _intent(side=OrderSide.SELL).side is OrderSide.SELL


def test_a_rebuilt_equal_contract_is_the_same_intent() -> None:
    rebuilt = FuturesContract(
        FuturesProductReference(Symbol("ES"), ExchangeCode("CME")), ExpirationDate("2026-03-20")
    )

    assert _intent(contract=rebuilt) == _intent()


def test_the_field_shape_is_exactly_the_approved_contract() -> None:
    """No fill quote, fill instant, provider, economics or research action."""
    assert [field.name for field in fields(FuturesExecutionIntent)] == [
        "portfolio_identity",
        "contract",
        "side",
        "contracts",
        "strategy_identity",
        "decided_at",
    ]


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("portfolio_identity", "portfolio identity cannot be None"),
        ("contract", "contract cannot be None"),
        ("side", "side cannot be None"),
        ("contracts", "contracts cannot be None"),
        ("strategy_identity", "strategy identity cannot be None"),
        ("decided_at", "decision instant cannot be None"),
    ],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidFuturesExecutionIntentError, match=message):
        _intent(**{field: None})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("portfolio_identity", "paper-1", "must be a PaperPortfolioIdentity"),
        ("portfolio_identity", StrategyIdentity("paper-1"), "must be a PaperPortfolioIdentity"),
        ("contract", _ES, "must be a FuturesContract"),
        (
            "contract",
            ListingReference(Symbol("ES"), ExchangeCode("CME")),
            "must be a FuturesContract",
        ),
        ("side", "BUY", "must be an OrderSide"),
        ("contracts", 2, "must be a FuturesContractCount"),
        ("contracts", Quantity("2"), "must be a FuturesContractCount"),
        ("strategy_identity", "alpha", "must be a StrategyIdentity"),
        ("strategy_identity", PaperPortfolioIdentity("alpha"), "must be a StrategyIdentity"),
        ("decided_at", "2026-01-20T22:00:00Z", "must be a PointInTime"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidFuturesExecutionIntentError, match=message):
        _intent(**{field: value})


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesExecutionIntentError, ValidationError)


def test_intent_is_immutable() -> None:
    intent = _intent()

    with pytest.raises(AttributeError):
        intent.side = OrderSide.SELL  # type: ignore[misc]
    with pytest.raises(AttributeError):
        intent.contracts = FuturesContractCount(3)  # type: ignore[misc]


def test_equivalent_intents_compare_and_hash_equal() -> None:
    assert _intent() == _intent()
    assert hash(_intent()) == hash(_intent())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("portfolio_identity", PaperPortfolioIdentity("paper-2")),
        ("contract", FuturesContract(_ES, ExpirationDate("2026-06-19"))),
        ("side", OrderSide.SELL),
        ("contracts", FuturesContractCount(3)),
        ("strategy_identity", StrategyIdentity("zeta")),
        ("decided_at", PointInTime("2026-01-21T22:00:00Z")),
    ],
)
def test_intents_differing_in_any_member_are_not_equal(field: str, value: object) -> None:
    assert _intent() != _intent(**{field: value})


def test_offset_equivalent_decision_instants_are_the_same_intent() -> None:
    assert _intent(decided_at=PointInTime("2026-01-21T03:30:00+05:30")) == _intent()
