"""Tests for the completed simulated execution of one futures paper order."""

from __future__ import annotations

from dataclasses import fields
from decimal import Decimal

import pytest

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
    FuturesExecutionIntent,
    FuturesPaperFill,
    InvalidFuturesPaperFillError,
    OrderSide,
    PaperFillIdentity,
    PaperOrderIdentity,
    PaperPortfolioIdentity,
)
from northstar_core.strategy import StrategyIdentity

_PORTFOLIO = PaperPortfolioIdentity("paper-1")
_CL = FuturesProductReference(Symbol("CL"), ExchangeCode("NYMEX"))
_CONTRACT = FuturesContract(_CL, ExpirationDate("2020-05-19"))
_STRATEGY = StrategyIdentity("alpha")
_DECIDED_AT = PointInTime("2020-04-17T22:00:00Z")
_NEXT_BAR = PointInTime("2020-04-20T22:00:00Z")


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


_INTENT = _intent()


def _fill(**overrides: object) -> FuturesPaperFill:
    values: dict[str, object] = {
        "identity": PaperFillIdentity("fill-1"),
        "order_identity": PaperOrderIdentity("order-1"),
        "intent": _INTENT,
        "contracts": FuturesContractCount(2),
        "fill_quote": QuoteValue(Decimal("18.27")),
        "filled_at": _NEXT_BAR,
    }
    values.update(overrides)
    return FuturesPaperFill(**values)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_fill_preserves_every_member() -> None:
    fill = _fill()

    assert fill.identity == PaperFillIdentity("fill-1")
    assert fill.order_identity == PaperOrderIdentity("order-1")
    assert fill.intent is _INTENT
    assert fill.contracts == FuturesContractCount(2)
    assert fill.fill_quote == QuoteValue(Decimal("18.27"))
    assert fill.filled_at == _NEXT_BAR


def test_fill_exposes_intent_facts_as_derived_values() -> None:
    fill = _fill(intent=_intent(side=OrderSide.SELL), contracts=FuturesContractCount(2))

    assert fill.portfolio_identity == _PORTFOLIO
    assert fill.contract == _CONTRACT
    assert fill.side is OrderSide.SELL
    assert fill.strategy_identity == _STRATEGY
    assert fill.decided_at == _DECIDED_AT


def test_derived_values_are_not_stored_as_independent_fields() -> None:
    assert [field.name for field in fields(FuturesPaperFill)] == [
        "identity",
        "order_identity",
        "intent",
        "contracts",
        "fill_quote",
        "filled_at",
    ]


# ---------------------------------------------------------------------------
# Quotation sign
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("quote", ["18.27", "0", "-37.63"])
def test_positive_zero_and_negative_fill_quotes_are_accepted(quote: str) -> None:
    assert _fill(fill_quote=QuoteValue(Decimal(quote))).fill_quote.value == Decimal(quote)


def test_a_price_is_not_a_fill_quote() -> None:
    with pytest.raises(InvalidFuturesPaperFillError, match="must be a QuoteValue"):
        _fill(fill_quote=Price("18.27", Currency("USD")))


# ---------------------------------------------------------------------------
# Full fills only
# ---------------------------------------------------------------------------


def test_contracts_equal_to_the_intent_are_accepted() -> None:
    intent = _intent(contracts=FuturesContractCount(5))

    assert _fill(intent=intent, contracts=FuturesContractCount(5)).contracts.value == 5


@pytest.mark.parametrize("count", [1, 3])
def test_mismatched_contracts_are_rejected(count: int) -> None:
    with pytest.raises(InvalidFuturesPaperFillError, match="partial fills are not supported"):
        _fill(contracts=FuturesContractCount(count))


# ---------------------------------------------------------------------------
# Temporal invariant: strictly after the decision
# ---------------------------------------------------------------------------


def test_fill_after_the_decision_is_accepted() -> None:
    assert _fill(filled_at=_NEXT_BAR).filled_at == _NEXT_BAR


def test_fill_exactly_at_the_decision_is_rejected() -> None:
    with pytest.raises(InvalidFuturesPaperFillError, match="strictly after"):
        _fill(filled_at=_DECIDED_AT)


def test_fill_before_the_decision_is_rejected() -> None:
    with pytest.raises(InvalidFuturesPaperFillError, match="strictly after"):
        _fill(filled_at=PointInTime("2020-04-16T22:00:00Z"))


def test_offset_equivalent_decision_instant_is_still_not_after() -> None:
    """Same instant in another offset spelling is equal, so it is rejected."""
    equivalent = PointInTime("2020-04-18T03:30:00+05:30")

    assert equivalent.compare(_DECIDED_AT) == 0
    with pytest.raises(InvalidFuturesPaperFillError, match="strictly after"):
        _fill(filled_at=equivalent)


def test_offset_spelled_instant_one_second_later_is_accepted() -> None:
    later = PointInTime("2020-04-18T03:30:01+05:30")

    assert _fill(filled_at=later).filled_at == PointInTime("2020-04-17T22:00:01Z")


def test_sub_second_fill_after_a_whole_second_decision_is_accepted() -> None:
    """Text ordering puts '.1Z' before 'Z'; chronological comparison does not."""
    fractional = PointInTime("2020-04-17T22:00:00.1Z")

    assert fractional.value < _DECIDED_AT.value
    assert _fill(filled_at=fractional).filled_at == fractional


def test_whole_second_fill_before_a_sub_second_decision_is_rejected() -> None:
    intent = _intent(decided_at=PointInTime("2020-04-17T22:00:00.1Z"))

    with pytest.raises(InvalidFuturesPaperFillError, match="strictly after"):
        _fill(intent=intent, filled_at=_DECIDED_AT)


# ---------------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("identity", "identity cannot be None"),
        ("order_identity", "order identity cannot be None"),
        ("intent", "intent cannot be None"),
        ("contracts", "contracts cannot be None"),
        ("fill_quote", "fill quote cannot be None"),
        ("filled_at", "fill instant cannot be None"),
    ],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidFuturesPaperFillError, match=message):
        _fill(**{field: None})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("identity", "fill-1", "must be a PaperFillIdentity"),
        ("identity", PaperOrderIdentity("fill-1"), "must be a PaperFillIdentity"),
        ("order_identity", "order-1", "must be a PaperOrderIdentity"),
        ("order_identity", PaperFillIdentity("order-1"), "must be a PaperOrderIdentity"),
        ("intent", "intent", "must be a FuturesExecutionIntent"),
        ("contracts", 2, "must be a FuturesContractCount"),
        ("fill_quote", Decimal("18.27"), "must be a QuoteValue"),
        ("filled_at", "2020-04-20T22:00:00Z", "must be a PointInTime"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidFuturesPaperFillError, match=message):
        _fill(**{field: value})


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesPaperFillError, ValidationError)


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_fill_is_immutable() -> None:
    fill = _fill()

    with pytest.raises(AttributeError):
        fill.fill_quote = QuoteValue(Decimal("1"))  # type: ignore[misc]


def test_equivalent_fills_compare_and_hash_equal() -> None:
    assert _fill() == _fill()
    assert hash(_fill()) == hash(_fill())
    assert _fill() == _fill(fill_quote=QuoteValue(Decimal("18.270")))
    assert _fill() == _fill(filled_at=PointInTime("2020-04-21T03:30:00+05:30"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("identity", PaperFillIdentity("fill-2")),
        ("order_identity", PaperOrderIdentity("order-2")),
        ("fill_quote", QuoteValue(Decimal("18.28"))),
        ("filled_at", PointInTime("2020-04-21T22:00:00Z")),
    ],
)
def test_fills_differing_in_any_member_are_not_equal(field: str, value: object) -> None:
    assert _fill() != _fill(**{field: value})
