"""Tests for the approved intent to execute one simulated trade."""

from __future__ import annotations

from decimal import Decimal

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
    InvalidExecutionIntentError,
    OrderSide,
    PaperPortfolioIdentity,
)
from northstar_core.strategy import StrategyIdentity

_PORTFOLIO = PaperPortfolioIdentity("paper-1")
_LISTING = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))
_STRATEGY = StrategyIdentity("alpha")
_DECIDED_AT = PointInTime("2026-01-20T16:00:00Z")


def _intent(**overrides: object) -> ExecutionIntent:
    values: dict[str, object] = {
        "portfolio_identity": _PORTFOLIO,
        "listing_reference": _LISTING,
        "side": OrderSide.BUY,
        "quantity": Quantity("10"),
        "strategy_identity": _STRATEGY,
        "decided_at": _DECIDED_AT,
    }
    values.update(overrides)
    return ExecutionIntent(**values)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_intent_preserves_every_member() -> None:
    intent = _intent()

    assert intent.portfolio_identity == _PORTFOLIO
    assert intent.listing_reference == _LISTING
    assert intent.side is OrderSide.BUY
    assert intent.quantity == Quantity("10")
    assert intent.strategy_identity == _STRATEGY
    assert intent.decided_at == _DECIDED_AT


def test_both_directions_are_constructible() -> None:
    assert _intent(side=OrderSide.BUY).side is OrderSide.BUY
    assert _intent(side=OrderSide.SELL).side is OrderSide.SELL


def test_fractional_quantities_are_accepted() -> None:
    assert _intent(quantity=Quantity("0.5")).quantity.value == Decimal("0.5")


# ---------------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("portfolio_identity", "portfolio identity cannot be None"),
        ("listing_reference", "listing reference cannot be None"),
        ("side", "side cannot be None"),
        ("quantity", "quantity cannot be None"),
        ("strategy_identity", "strategy identity cannot be None"),
        ("decided_at", "decision instant cannot be None"),
    ],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidExecutionIntentError, match=message):
        _intent(**{field: None})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("portfolio_identity", "paper-1", "must be a PaperPortfolioIdentity"),
        ("listing_reference", "AAPL@NASDAQ", "must be a ListingReference"),
        ("side", "BUY", "must be an OrderSide"),
        ("quantity", 10, "must be a Quantity"),
        ("quantity", Decimal("10"), "must be a Quantity"),
        ("strategy_identity", "alpha", "must be a StrategyIdentity"),
        ("decided_at", "2026-01-20T16:00:00Z", "must be a PointInTime"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidExecutionIntentError, match=message):
        _intent(**{field: value})


def test_a_plain_string_side_is_rejected() -> None:
    """OrderSide members are strings, so the check must be on the type, not the value."""
    with pytest.raises(InvalidExecutionIntentError, match="must be an OrderSide"):
        _intent(side="BUY")


def test_another_identity_kind_is_not_a_portfolio_identity() -> None:
    with pytest.raises(InvalidExecutionIntentError, match="must be a PaperPortfolioIdentity"):
        _intent(portfolio_identity=StrategyIdentity("paper-1"))


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidExecutionIntentError, ValidationError)
    with pytest.raises(ValidationError):
        _intent(quantity=None)


# ---------------------------------------------------------------------------
# Quantity invariant
# ---------------------------------------------------------------------------


def test_zero_quantity_is_rejected() -> None:
    """An intent to trade nothing is not an intent; it must not stand in for a hold."""
    with pytest.raises(InvalidExecutionIntentError, match="must be greater than zero"):
        _intent(quantity=Quantity("0"))


def test_zero_quantity_is_rejected_in_every_spelling() -> None:
    for zero in ("0", "0.0", "0.000", Decimal("0E-10")):
        with pytest.raises(InvalidExecutionIntentError, match="must be greater than zero"):
            _intent(quantity=Quantity(zero))


def test_smallest_positive_quantity_is_accepted() -> None:
    assert _intent(quantity=Quantity("0.00000001")).quantity.value > 0


# ---------------------------------------------------------------------------
# HOLD is unrepresentable
# ---------------------------------------------------------------------------


def test_hold_cannot_reach_an_intent() -> None:
    """There is no HOLD member, so a hold cannot be expressed as a direction."""
    with pytest.raises(ValueError):
        _intent(side=OrderSide("HOLD"))


def test_every_intent_has_a_tradeable_direction() -> None:
    assert _intent().side in (OrderSide.BUY, OrderSide.SELL)


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_intent_is_immutable() -> None:
    intent = _intent()

    with pytest.raises(AttributeError):
        intent.quantity = Quantity("20")
    with pytest.raises(AttributeError):
        intent.side = OrderSide.SELL


def test_equivalent_intents_compare_and_hash_equal() -> None:
    assert _intent() == _intent()
    assert hash(_intent()) == hash(_intent())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("portfolio_identity", PaperPortfolioIdentity("paper-2")),
        ("listing_reference", ListingReference(Symbol("MSFT"), ExchangeCode("NASDAQ"))),
        ("side", OrderSide.SELL),
        ("quantity", Quantity("11")),
        ("strategy_identity", StrategyIdentity("zeta")),
        ("decided_at", PointInTime("2026-01-21T16:00:00Z")),
    ],
)
def test_intents_differing_in_any_member_are_not_equal(field: str, value: object) -> None:
    assert _intent() != _intent(**{field: value})


def test_offset_equivalent_decision_instants_are_the_same_intent() -> None:
    """PointInTime canonicalises to UTC, so an offset spelling is the same instant."""
    assert _intent(decided_at=PointInTime("2026-01-20T21:30:00+05:30")) == _intent()


def test_intent_is_usable_as_a_dictionary_key() -> None:
    assert {_intent(): "kept"}[_intent()] == "kept"


def test_string_and_repr_forms_expose_the_intent() -> None:
    intent = _intent()

    assert str(intent) == "BUY 10 AAPL@NASDAQ paper-1 alpha 2026-01-20T16:00:00Z"
    assert repr(intent).startswith("ExecutionIntent(portfolio_identity=")
