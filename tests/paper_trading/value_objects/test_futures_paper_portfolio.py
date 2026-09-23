"""Tests for the immutable futures holdings of one paper portfolio."""

from __future__ import annotations

from dataclasses import fields
from decimal import Decimal

import pytest

from northstar_core.derivatives import ExpirationDate, QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, PointInTime, Symbol
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.paper_trading import (
    FuturesPaperPortfolio,
    FuturesPosition,
    InvalidFuturesPaperPortfolioError,
    PaperPortfolioIdentity,
)
from northstar_core.strategy import StrategyIdentity

_IDENTITY = PaperPortfolioIdentity("paper-1")
_STRATEGY = StrategyIdentity("alpha")
_AS_OF = PointInTime("2026-01-20T22:00:00Z")

_MARCH = ExpirationDate("2026-03-20")
_JUNE = ExpirationDate("2026-06-19")
_CL = FuturesProductReference(Symbol("CL"), ExchangeCode("NYMEX"))
_ES = FuturesProductReference(Symbol("ES"), ExchangeCode("CME"))
_ES_CBOT = FuturesProductReference(Symbol("ES"), ExchangeCode("CBOT"))
_MES = FuturesProductReference(Symbol("MES"), ExchangeCode("CME"))

_CL_MARCH = FuturesContract(_CL, _MARCH)
_ES_MARCH = FuturesContract(_ES, _MARCH)
_ES_JUNE = FuturesContract(_ES, _JUNE)
_ES_CBOT_MARCH = FuturesContract(_ES_CBOT, _MARCH)
_MES_MARCH = FuturesContract(_MES, _MARCH)


def _position(contract: FuturesContract, net: int = 1, entry: str = "100") -> FuturesPosition:
    return FuturesPosition(contract, net, QuoteValue(Decimal(entry)))


def _portfolio(**overrides: object) -> FuturesPaperPortfolio:
    values: dict[str, object] = {
        "identity": _IDENTITY,
        "strategy_identity": _STRATEGY,
        "positions": (_position(_ES_MARCH),),
        "as_of": _AS_OF,
    }
    values.update(overrides)
    return FuturesPaperPortfolio(**values)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_empty_portfolio_is_valid_and_retains_its_strategy() -> None:
    portfolio = _portfolio(positions=())

    assert portfolio.positions == ()
    assert portfolio.position_count == 0
    assert portfolio.identity == _IDENTITY
    assert portfolio.strategy_identity == _STRATEGY
    assert portfolio.as_of == _AS_OF


def test_empty_portfolios_for_different_strategies_are_distinct() -> None:
    assert _portfolio(positions=()) != _portfolio(
        positions=(), strategy_identity=StrategyIdentity("zeta")
    )


def test_one_long_position() -> None:
    portfolio = _portfolio(positions=(_position(_ES_MARCH, 2),))

    assert portfolio.get_position(_ES_MARCH).is_long


def test_one_short_position() -> None:
    portfolio = _portfolio(positions=(_position(_ES_MARCH, -2),))

    assert portfolio.get_position(_ES_MARCH).is_short


def test_several_contracts_in_canonical_order() -> None:
    positions = (
        _position(_CL_MARCH, -1, "-37.63"),
        _position(_ES_CBOT_MARCH, 1),
        _position(_ES_MARCH, 3, "0"),
        _position(_ES_JUNE, -2),
        _position(_MES_MARCH, 4),
    )

    portfolio = _portfolio(positions=positions)

    assert portfolio.positions == positions
    assert portfolio.position_count == 5


def test_different_expiries_of_one_product_coexist_independently() -> None:
    portfolio = _portfolio(positions=(_position(_ES_MARCH, 1), _position(_ES_JUNE, -1)))

    assert portfolio.get_position(_ES_MARCH).net_contracts == 1
    assert portfolio.get_position(_ES_JUNE).net_contracts == -1


def test_get_position_returns_none_when_flat() -> None:
    assert _portfolio().get_position(_ES_JUNE) is None


def test_get_position_accepts_a_rebuilt_equal_contract() -> None:
    rebuilt = FuturesContract(
        FuturesProductReference(Symbol("ES"), ExchangeCode("CME")), ExpirationDate("2026-03-20")
    )

    assert _portfolio().get_position(rebuilt) == _position(_ES_MARCH)


@pytest.mark.parametrize(
    ("value", "message"),
    [(None, "contract cannot be None"), (_ES, "must be a FuturesContract")],
)
def test_get_position_rejects_a_non_contract(value: object, message: str) -> None:
    with pytest.raises(InvalidFuturesPaperPortfolioError, match=message):
        _portfolio().get_position(value)


# ---------------------------------------------------------------------------
# Position invariants
# ---------------------------------------------------------------------------


def test_duplicate_contract_is_rejected() -> None:
    with pytest.raises(InvalidFuturesPaperPortfolioError, match="two positions for one contract"):
        _portfolio(positions=(_position(_ES_MARCH, 1), _position(_ES_MARCH, -1)))


def test_duplicate_rebuilt_equal_contract_is_rejected() -> None:
    rebuilt = FuturesContract(
        FuturesProductReference(Symbol("ES"), ExchangeCode("CME")), ExpirationDate("2026-03-20")
    )

    with pytest.raises(InvalidFuturesPaperPortfolioError, match="two positions for one contract"):
        _portfolio(positions=(_position(_ES_MARCH), _position(rebuilt, 2)))


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (_ES_JUNE, _ES_MARCH),
        (_MES_MARCH, _ES_MARCH),
        (_ES_MARCH, _CL_MARCH),
        (_ES_MARCH, _ES_CBOT_MARCH),
    ],
)
def test_out_of_order_positions_are_rejected(
    first: FuturesContract, second: FuturesContract
) -> None:
    """Order is required of the caller, never silently imposed."""
    with pytest.raises(InvalidFuturesPaperPortfolioError, match="must be ordered"):
        _portfolio(positions=(_position(first), _position(second)))


def test_positions_must_be_a_tuple() -> None:
    with pytest.raises(InvalidFuturesPaperPortfolioError, match="must be a tuple"):
        _portfolio(positions=[_position(_ES_MARCH)])


def test_positions_cannot_be_none() -> None:
    with pytest.raises(InvalidFuturesPaperPortfolioError, match="positions cannot be None"):
        _portfolio(positions=None)


@pytest.mark.parametrize("member", [None, _ES_MARCH, "position"])
def test_non_position_members_are_rejected(member: object) -> None:
    with pytest.raises(InvalidFuturesPaperPortfolioError, match="must contain FuturesPosition"):
        _portfolio(positions=(member,))


# ---------------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("identity", "identity cannot be None"),
        ("strategy_identity", "strategy identity cannot be None"),
        ("as_of", "as-of instant cannot be None"),
    ],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidFuturesPaperPortfolioError, match=message):
        _portfolio(**{field: None})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("identity", "paper-1", "must be a PaperPortfolioIdentity"),
        ("identity", StrategyIdentity("paper-1"), "must be a PaperPortfolioIdentity"),
        ("strategy_identity", "alpha", "must be a StrategyIdentity"),
        ("strategy_identity", PaperPortfolioIdentity("alpha"), "must be a StrategyIdentity"),
        ("as_of", "2026-01-20T22:00:00Z", "must be a PointInTime"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidFuturesPaperPortfolioError, match=message):
        _portfolio(**{field: value})


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesPaperPortfolioError, ValidationError)


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_portfolio_is_immutable() -> None:
    portfolio = _portfolio()

    with pytest.raises(AttributeError):
        portfolio.positions = ()  # type: ignore[misc]


def test_equivalent_portfolios_compare_and_hash_equal() -> None:
    assert _portfolio() == _portfolio()
    assert hash(_portfolio()) == hash(_portfolio())
    assert _portfolio() == _portfolio(as_of=PointInTime("2026-01-21T03:30:00+05:30"))


def test_the_field_shape_carries_no_provider_price_or_currency() -> None:
    names = [field.name for field in fields(FuturesPaperPortfolio)]

    assert names == ["identity", "strategy_identity", "positions", "as_of"]
    for forbidden in ("provider", "price", "currency", "cash", "pnl", "margin", "fills"):
        assert not any(forbidden in name for name in names)
