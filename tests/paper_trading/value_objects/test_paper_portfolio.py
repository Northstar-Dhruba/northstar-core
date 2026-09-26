"""Tests for the immutable holdings of one paper portfolio."""

from __future__ import annotations

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
    InvalidPaperPortfolioError,
    PaperPortfolio,
    PaperPortfolioIdentity,
    Position,
)

_USD = Currency("USD")
_IDENTITY = PaperPortfolioIdentity("paper-1")
_AS_OF = PointInTime("2026-01-20T16:00:00Z")

_NASDAQ = ExchangeCode("NASDAQ")
_LSE = ExchangeCode("LSE")

_AAPL = ListingReference(Symbol("AAPL"), _NASDAQ)
_MSFT = ListingReference(Symbol("MSFT"), _NASDAQ)
_ZM = ListingReference(Symbol("ZM"), _NASDAQ)
_AAPL_LSE = ListingReference(Symbol("AAPL"), _LSE)


def _position(listing_reference: ListingReference, quantity: str = "10") -> Position:
    return Position(listing_reference, Quantity(quantity), Price("100", _USD))


def _portfolio(**overrides: object) -> PaperPortfolio:
    values: dict[str, object] = {
        "identity": _IDENTITY,
        "positions": (_position(_AAPL),),
        "as_of": _AS_OF,
    }
    values.update(overrides)
    return PaperPortfolio(**values)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_empty_portfolio_is_valid() -> None:
    portfolio = _portfolio(positions=())

    assert portfolio.positions == ()
    assert portfolio.position_count == 0
    assert portfolio.identity == _IDENTITY
    assert portfolio.as_of == _AS_OF


def test_one_position_is_preserved() -> None:
    portfolio = _portfolio()

    assert portfolio.position_count == 1
    assert portfolio.positions == (_position(_AAPL),)


def test_multiple_positions_are_preserved_in_order() -> None:
    positions = (_position(_AAPL), _position(_MSFT), _position(_ZM))

    portfolio = _portfolio(positions=positions)

    assert portfolio.position_count == 3
    assert portfolio.positions == positions


def test_as_of_is_preserved_exactly() -> None:
    instant = PointInTime("2019-07-04T13:30:00Z")

    assert _portfolio(as_of=instant).as_of == instant


# ---------------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("identity", "identity cannot be None"),
        ("positions", "positions cannot be None"),
        ("as_of", "as-of instant cannot be None"),
    ],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidPaperPortfolioError, match=message):
        _portfolio(**{field: None})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("identity", "paper-1", "must be a PaperPortfolioIdentity"),
        ("as_of", "2026-01-20T16:00:00Z", "must be a PointInTime"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidPaperPortfolioError, match=message):
        _portfolio(**{field: value})


@pytest.mark.parametrize("value", [[], [_position(_AAPL)], {_position(_AAPL)}, "positions"])
def test_positions_must_be_a_tuple(value: object) -> None:
    with pytest.raises(InvalidPaperPortfolioError, match="positions must be a tuple"):
        _portfolio(positions=value)


@pytest.mark.parametrize("value", ["position", 1, None, _AAPL])
def test_positions_must_contain_position_values(value: object) -> None:
    with pytest.raises(InvalidPaperPortfolioError, match="must contain Position values"):
        _portfolio(positions=(value,))


def test_a_non_position_among_valid_positions_is_rejected() -> None:
    with pytest.raises(InvalidPaperPortfolioError, match="must contain Position values"):
        _portfolio(positions=(_position(_AAPL), "position"))


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidPaperPortfolioError, ValidationError)
    with pytest.raises(ValidationError):
        _portfolio(identity=None)


# ---------------------------------------------------------------------------
# One position per listing
# ---------------------------------------------------------------------------


def test_duplicate_listing_is_rejected() -> None:
    with pytest.raises(InvalidPaperPortfolioError, match="two positions for one listing"):
        _portfolio(positions=(_position(_AAPL), _position(_AAPL)))


def test_duplicate_listing_is_rejected_even_with_different_holdings() -> None:
    """The listing is the identity; quantity and price do not distinguish it."""
    with pytest.raises(InvalidPaperPortfolioError, match="two positions for one listing"):
        _portfolio(positions=(_position(_AAPL, "10"), _position(_AAPL, "20")))


def test_non_adjacent_duplicate_listing_is_rejected() -> None:
    with pytest.raises(InvalidPaperPortfolioError, match="two positions for one listing"):
        _portfolio(positions=(_position(_AAPL), _position(_MSFT), _position(_AAPL)))


def test_the_same_symbol_on_different_exchanges_stays_distinct() -> None:
    """AAPL@LSE and AAPL@NASDAQ are two listings, not one."""
    portfolio = _portfolio(positions=(_position(_AAPL_LSE), _position(_AAPL)))

    assert portfolio.position_count == 2
    assert portfolio.get_position(_AAPL_LSE) != portfolio.get_position(_AAPL)


# ---------------------------------------------------------------------------
# Canonical ordering
# ---------------------------------------------------------------------------


def test_positions_out_of_symbol_order_are_rejected() -> None:
    with pytest.raises(InvalidPaperPortfolioError, match="ordered by symbol, then exchange code"):
        _portfolio(positions=(_position(_MSFT), _position(_AAPL)))


def test_positions_out_of_exchange_order_are_rejected() -> None:
    """Same symbol, so the exchange code decides: LSE precedes NASDAQ."""
    with pytest.raises(InvalidPaperPortfolioError, match="ordered by symbol, then exchange code"):
        _portfolio(positions=(_position(_AAPL), _position(_AAPL_LSE)))


def test_exchange_order_applies_only_within_one_symbol() -> None:
    """A later symbol on an earlier exchange is still correctly ordered."""
    msft_lse = ListingReference(Symbol("MSFT"), _LSE)

    portfolio = _portfolio(positions=(_position(_AAPL), _position(msft_lse)))

    assert portfolio.position_count == 2


def test_a_single_misplaced_position_is_rejected() -> None:
    with pytest.raises(InvalidPaperPortfolioError, match="ordered by symbol, then exchange code"):
        _portfolio(positions=(_position(_AAPL), _position(_ZM), _position(_MSFT)))


def test_the_value_object_never_sorts_silently() -> None:
    """Unordered input is rejected, not quietly corrected."""
    unordered = (_position(_ZM), _position(_AAPL))

    with pytest.raises(InvalidPaperPortfolioError):
        _portfolio(positions=unordered)

    def _key(position: Position) -> tuple[str, str]:
        listing = position.listing_reference
        return (listing.symbol.value, listing.exchange_code.value)

    ordered = tuple(sorted(unordered, key=_key))
    assert _portfolio(positions=ordered).positions == ordered


def test_canonical_order_is_symbol_then_exchange() -> None:
    positions = (
        _position(_AAPL_LSE),
        _position(_AAPL),
        _position(_MSFT),
        _position(_ZM),
    )

    portfolio = _portfolio(positions=positions)

    assert [
        (p.listing_reference.symbol.value, p.listing_reference.exchange_code.value)
        for p in portfolio.positions
    ] == [("AAPL", "LSE"), ("AAPL", "NASDAQ"), ("MSFT", "NASDAQ"), ("ZM", "NASDAQ")]


def test_an_empty_and_single_portfolio_are_trivially_ordered() -> None:
    assert _portfolio(positions=()).position_count == 0
    assert _portfolio(positions=(_position(_ZM),)).position_count == 1


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


def test_get_position_returns_the_held_position() -> None:
    portfolio = _portfolio(positions=(_position(_AAPL, "7"), _position(_MSFT, "3")))

    assert portfolio.get_position(_AAPL) == _position(_AAPL, "7")
    assert portfolio.get_position(_MSFT) == _position(_MSFT, "3")


def test_get_position_returns_none_when_not_held() -> None:
    portfolio = _portfolio(positions=(_position(_AAPL),))

    assert portfolio.get_position(_MSFT) is None


def test_get_position_returns_none_on_an_empty_portfolio() -> None:
    assert _portfolio(positions=()).get_position(_AAPL) is None


def test_get_position_distinguishes_exchanges() -> None:
    portfolio = _portfolio(positions=(_position(_AAPL_LSE, "5"),))

    assert portfolio.get_position(_AAPL_LSE) == _position(_AAPL_LSE, "5")
    assert portfolio.get_position(_AAPL) is None


def test_get_position_validates_its_argument() -> None:
    portfolio = _portfolio()

    with pytest.raises(InvalidPaperPortfolioError, match="listing reference cannot be None"):
        portfolio.get_position(None)
    with pytest.raises(InvalidPaperPortfolioError, match="must be a ListingReference"):
        portfolio.get_position("AAPL@NASDAQ")


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_portfolio_is_immutable() -> None:
    portfolio = _portfolio()

    with pytest.raises(AttributeError):
        portfolio.positions = ()
    with pytest.raises(AttributeError):
        portfolio.as_of = PointInTime("2026-02-01T16:00:00Z")


def test_equivalent_portfolios_compare_and_hash_equal() -> None:
    assert _portfolio() == _portfolio()
    assert hash(_portfolio()) == hash(_portfolio())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("identity", PaperPortfolioIdentity("paper-2")),
        ("positions", ()),
        ("as_of", PointInTime("2026-02-01T16:00:00Z")),
    ],
)
def test_portfolios_differing_in_any_member_are_not_equal(field: str, value: object) -> None:
    assert _portfolio() != _portfolio(**{field: value})


def test_portfolios_differing_only_by_held_quantity_are_not_equal() -> None:
    assert _portfolio(positions=(_position(_AAPL, "10"),)) != _portfolio(
        positions=(_position(_AAPL, "11"),)
    )


def test_offset_equivalent_as_of_instants_are_the_same_snapshot() -> None:
    assert _portfolio(as_of=PointInTime("2026-01-20T21:30:00+05:30")) == _portfolio()


def test_portfolio_is_usable_as_a_dictionary_key() -> None:
    assert {_portfolio(): "kept"}[_portfolio()] == "kept"


def test_string_and_repr_forms_expose_the_snapshot() -> None:
    portfolio = _portfolio()

    assert str(portfolio) == "paper-1 2026-01-20T16:00:00Z positions=1"
    assert repr(portfolio).startswith("PaperPortfolio(identity=")


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------


def test_portfolio_carries_no_cash_or_valuation_meaning() -> None:
    portfolio = _portfolio()

    for absent in (
        "cash",
        "balance",
        "buying_power",
        "market_value",
        "realised_pnl",
        "unrealised_pnl",
        "margin",
        "leverage",
    ):
        assert not hasattr(portfolio, absent)


def test_portfolio_exposes_no_mutation_or_folding_behaviour() -> None:
    portfolio = _portfolio()

    for absent in ("apply", "apply_fill", "add", "remove", "update", "fold", "save", "store"):
        assert not hasattr(portfolio, absent)
