"""Tests for the completed simulated execution of one paper order."""

from __future__ import annotations

from decimal import Decimal

import pytest

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    Currency,
    ExchangeCode,
    PointInTime,
    Price,
    Quantity,
    Symbol,
)
from northstar_core.paper_trading import (
    ExecutionIntent,
    InvalidPaperFillError,
    OrderSide,
    PaperFill,
    PaperFillIdentity,
    PaperOrderIdentity,
    PaperPortfolioIdentity,
)
from northstar_core.strategy import StrategyIdentity

_USD = Currency("USD")
_PORTFOLIO = PaperPortfolioIdentity("paper-1")
_LISTING = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))
_STRATEGY = StrategyIdentity("alpha")
_DECIDED_AT = PointInTime("2026-01-20T16:00:00Z")
_INTENT = ExecutionIntent(
    _PORTFOLIO, _LISTING, OrderSide.BUY, Quantity("10"), _STRATEGY, _DECIDED_AT
)


def _fill(**overrides: object) -> PaperFill:
    values: dict[str, object] = {
        "identity": PaperFillIdentity("fill-1"),
        "order_identity": PaperOrderIdentity("order-1"),
        "intent": _INTENT,
        "quantity": Quantity("10"),
        "price": Price("100", _USD),
        "filled_at": _DECIDED_AT,
    }
    values.update(overrides)
    return PaperFill(**values)


def _intent_with(**overrides: object) -> ExecutionIntent:
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


def test_fill_preserves_every_member() -> None:
    fill = _fill()

    assert fill.identity == PaperFillIdentity("fill-1")
    assert fill.order_identity == PaperOrderIdentity("order-1")
    assert fill.intent == _INTENT
    assert fill.quantity == Quantity("10")
    assert fill.price == Price("100", _USD)
    assert fill.filled_at == _DECIDED_AT


def test_a_sell_fill_is_constructible() -> None:
    intent = _intent_with(side=OrderSide.SELL)

    assert _fill(intent=intent).side is OrderSide.SELL


# ---------------------------------------------------------------------------
# Self-sufficiency: everything needed for reconstruction comes from the intent
# ---------------------------------------------------------------------------


def test_fill_exposes_portfolio_listing_side_and_strategy_through_its_intent() -> None:
    """A fill alone must identify what it belongs to, without its order."""
    fill = _fill()

    assert fill.portfolio_identity == _PORTFOLIO
    assert fill.listing_reference == _LISTING
    assert fill.side is OrderSide.BUY
    assert fill.strategy_identity == _STRATEGY
    assert fill.decided_at == _DECIDED_AT


def test_derived_values_follow_the_intent_they_executed() -> None:
    intent = _intent_with(
        portfolio_identity=PaperPortfolioIdentity("paper-2"),
        listing_reference=ListingReference(Symbol("MSFT"), ExchangeCode("NASDAQ")),
        side=OrderSide.SELL,
        strategy_identity=StrategyIdentity("zeta"),
    )

    fill = _fill(intent=intent)

    assert fill.portfolio_identity == PaperPortfolioIdentity("paper-2")
    assert fill.listing_reference == ListingReference(Symbol("MSFT"), ExchangeCode("NASDAQ"))
    assert fill.side is OrderSide.SELL
    assert fill.strategy_identity == StrategyIdentity("zeta")


def test_derived_values_are_not_stored_as_independent_fields() -> None:
    """Derived, never duplicated, so a fill cannot disagree with its intent."""
    fill = _fill()

    assert "portfolio_identity" not in PaperFill.__slots__
    assert "listing_reference" not in PaperFill.__slots__
    assert "side" not in PaperFill.__slots__
    assert "strategy_identity" not in PaperFill.__slots__
    assert fill.portfolio_identity is fill.intent.portfolio_identity


@pytest.mark.parametrize(
    "name", ["portfolio_identity", "listing_reference", "side", "strategy_identity", "decided_at"]
)
def test_derived_values_are_read_only(name: str) -> None:
    fill = _fill()

    with pytest.raises(AttributeError):
        setattr(fill, name, None)


# ---------------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("identity", "identity cannot be None"),
        ("order_identity", "order identity cannot be None"),
        ("intent", "intent cannot be None"),
        ("quantity", "quantity cannot be None"),
        ("price", "price cannot be None"),
        ("filled_at", "fill instant cannot be None"),
    ],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidPaperFillError, match=message):
        _fill(**{field: None})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("identity", "fill-1", "must be a PaperFillIdentity"),
        ("order_identity", "order-1", "must be a PaperOrderIdentity"),
        ("intent", "intent", "must be an ExecutionIntent"),
        ("quantity", 10, "must be a Quantity"),
        ("price", 100, "must be a Price"),
        ("price", Decimal("100"), "must be a Price"),
        ("filled_at", "2026-01-20T16:00:00Z", "must be a PointInTime"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidPaperFillError, match=message):
        _fill(**{field: value})


def test_a_fill_identity_is_not_an_order_identity() -> None:
    with pytest.raises(InvalidPaperFillError, match="must be a PaperOrderIdentity"):
        _fill(order_identity=PaperFillIdentity("order-1"))


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidPaperFillError, ValidationError)
    with pytest.raises(ValidationError):
        _fill(price=None)


# ---------------------------------------------------------------------------
# Quantity invariants
# ---------------------------------------------------------------------------


def test_zero_quantity_is_rejected() -> None:
    with pytest.raises(InvalidPaperFillError, match="must be greater than zero"):
        _fill(quantity=Quantity("0"), intent=_intent_with(quantity=Quantity("10")))


def test_partial_fill_is_rejected() -> None:
    """A fill either executed the whole intent or does not exist."""
    with pytest.raises(InvalidPaperFillError, match="partial fills are not supported"):
        _fill(quantity=Quantity("4"))


def test_overfill_is_rejected() -> None:
    with pytest.raises(InvalidPaperFillError, match="partial fills are not supported"):
        _fill(quantity=Quantity("11"))


def test_quantity_must_equal_the_intended_quantity() -> None:
    intent = _intent_with(quantity=Quantity("2.5"))

    assert _fill(intent=intent, quantity=Quantity("2.5")).quantity == Quantity("2.5")
    with pytest.raises(InvalidPaperFillError, match="partial fills are not supported"):
        _fill(intent=intent, quantity=Quantity("2.50001"))


def test_equal_quantity_in_a_different_spelling_is_accepted() -> None:
    """Quantity normalizes, so 10 and 10.00 are the same intended size."""
    intent = _intent_with(quantity=Quantity("10.00"))

    assert _fill(intent=intent, quantity=Quantity("10")).quantity == Quantity("10")


# ---------------------------------------------------------------------------
# Price invariant
# ---------------------------------------------------------------------------


def test_zero_price_is_rejected() -> None:
    with pytest.raises(InvalidPaperFillError, match="price must be greater than zero"):
        _fill(price=Price("0", _USD))


def test_smallest_positive_price_is_accepted() -> None:
    assert _fill(price=Price("0.00000001", _USD)).price.amount > 0


def test_any_currency_is_accepted() -> None:
    assert _fill(price=Price("100", Currency("EUR"))).price.currency == Currency("EUR")


# ---------------------------------------------------------------------------
# Temporal invariant
# ---------------------------------------------------------------------------


def test_fill_at_the_decision_instant_is_accepted() -> None:
    """Simulated execution against decision-time evidence has no delay."""
    assert _fill(filled_at=_DECIDED_AT).filled_at == _DECIDED_AT


def test_fill_after_the_decision_instant_is_accepted() -> None:
    later = PointInTime("2026-01-21T16:00:00Z")

    assert _fill(filled_at=later).filled_at == later


def test_fill_before_the_decision_instant_is_rejected() -> None:
    with pytest.raises(InvalidPaperFillError, match="cannot precede the intent decision instant"):
        _fill(filled_at=PointInTime("2026-01-20T15:59:59Z"))


def test_fill_a_day_before_the_decision_is_rejected() -> None:
    with pytest.raises(InvalidPaperFillError, match="cannot precede the intent decision instant"):
        _fill(filled_at=PointInTime("2026-01-19T16:00:00Z"))


def test_offset_equivalent_fill_instant_is_accepted() -> None:
    """Same instant, different offset spelling: compared chronologically, not textually."""
    equivalent = PointInTime("2026-01-20T21:30:00+05:30")

    assert equivalent.compare(_DECIDED_AT) == 0
    assert _fill(filled_at=equivalent).filled_at == _DECIDED_AT


def test_offset_equivalent_decision_instant_is_accepted() -> None:
    intent = _intent_with(decided_at=PointInTime("2026-01-20T21:30:00+05:30"))

    assert _fill(intent=intent, filled_at=_DECIDED_AT).filled_at == _DECIDED_AT


def test_offset_spelled_instant_that_is_actually_earlier_is_rejected() -> None:
    with pytest.raises(InvalidPaperFillError, match="cannot precede the intent decision instant"):
        _fill(filled_at=PointInTime("2026-01-20T21:29:59+05:30"))


def test_sub_second_fill_after_a_whole_second_decision_is_accepted() -> None:
    """Text ordering puts '.1Z' before 'Z'; chronological comparison does not."""
    fractional = PointInTime("2026-01-20T16:00:00.1Z")

    assert fractional.value < _DECIDED_AT.value
    assert fractional.compare(_DECIDED_AT) > 0
    assert _fill(filled_at=fractional).filled_at == fractional


def test_whole_second_fill_before_a_sub_second_decision_is_rejected() -> None:
    intent = _intent_with(decided_at=PointInTime("2026-01-20T16:00:00.1Z"))

    with pytest.raises(InvalidPaperFillError, match="cannot precede the intent decision instant"):
        _fill(intent=intent, filled_at=_DECIDED_AT)


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_fill_is_immutable() -> None:
    fill = _fill()

    with pytest.raises(AttributeError):
        fill.quantity = Quantity("20")
    with pytest.raises(AttributeError):
        fill.price = Price("200", _USD)


def test_equivalent_fills_compare_and_hash_equal() -> None:
    assert _fill() == _fill()
    assert hash(_fill()) == hash(_fill())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("identity", PaperFillIdentity("fill-2")),
        ("order_identity", PaperOrderIdentity("order-2")),
        ("price", Price("101", _USD)),
        ("filled_at", PointInTime("2026-01-22T16:00:00Z")),
    ],
)
def test_fills_differing_in_any_member_are_not_equal(field: str, value: object) -> None:
    assert _fill() != _fill(**{field: value})


def test_fills_differing_only_by_currency_are_not_equal() -> None:
    assert _fill() != _fill(price=Price("100", Currency("EUR")))


def test_fill_is_usable_as_a_dictionary_key() -> None:
    assert {_fill(): "kept"}[_fill()] == "kept"


def test_string_and_repr_forms_expose_the_execution() -> None:
    fill = _fill()

    assert str(fill) == "fill-1 order-1 BUY 10 @ 100 USD 2026-01-20T16:00:00Z"
    assert repr(fill).startswith("PaperFill(identity=")
