"""Reference contract test suite for the Position subordinate entity.

This suite defines the Northstar Reference Subordinate Entity Contract for
Position.
"""

import pytest

from northstar_core.domain.exchange import Exchange
from northstar_core.domain.instrument import Instrument
from northstar_core.domain.listing import Listing
from northstar_core.domain.value_objects import ListingStatus, Tradability
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, ExchangeCode, Symbol
from northstar_core.portfolio import InvalidPositionError, Position


def _build_listing(symbol: str = "AAPL") -> Listing:
    return Listing(
        Instrument(Symbol(symbol), f"{symbol} Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        ListingStatus("Active"),
        Tradability("Permitted"),
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_position_from_listing():
    listing = _build_listing()

    position = Position(listing)

    assert position.listing is listing


def test_position_remains_a_subordinate_entity():
    position = Position(_build_listing())

    assert isinstance(position, Position)
    assert not hasattr(position, "position_identity")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none_listing():
    with pytest.raises(InvalidPositionError, match="listing cannot be None"):
        Position(None)


def test_rejects_invalid_listing_type():
    with pytest.raises(InvalidPositionError, match="listing must be a Listing"):
        Position("listing")


def test_invalid_position_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Position(None)


def test_invalid_position_error_is_a_value_error():
    with pytest.raises(ValueError):
        Position(None)


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def test_position_composes_only_listing():
    position = Position(_build_listing())

    assert isinstance(position.listing, Listing)


def test_position_does_not_compose_inherited_or_external_context():
    position = Position(_build_listing())

    assert not hasattr(position, "participant_reference")
    assert not hasattr(position, "point_in_time")
    assert not hasattr(position, "trade")
    assert not hasattr(position, "portfolio")
    assert not hasattr(position, "quote")
    assert not hasattr(position, "tick")
    assert not hasattr(position, "ohlc_bar")
    assert not hasattr(position, "order_book")


def test_listing_remains_authoritative_market_context():
    listing = _build_listing()
    position = Position(listing)

    assert position.listing.instrument.symbol == Symbol("AAPL")
    assert position.listing is listing


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_repr_contains_position_and_listing():
    representation = repr(Position(_build_listing()))

    assert "Position(" in representation
    assert "Listing(" in representation


# ---------------------------------------------------------------------------
# Mutability
# ---------------------------------------------------------------------------


def test_position_is_mutable():
    position = Position(_build_listing())
    replacement_listing = _build_listing("MSFT")

    position.listing = replacement_listing

    assert position.listing is replacement_listing


def test_listing_may_be_replaced():
    position = Position(_build_listing())
    replacement_listing = _build_listing("GOOG")

    position.listing = replacement_listing

    assert position.listing.instrument.symbol == Symbol("GOOG")


# ---------------------------------------------------------------------------
# Boundary Protection
# ---------------------------------------------------------------------------


def test_position_has_no_independent_aggregate_behavior():
    position = Position(_build_listing())

    assert not hasattr(position, "portfolio_identity")
    assert not hasattr(position, "positions")
    assert not hasattr(position, "aggregate_consistency")


def test_position_inherits_participant_and_temporal_context_from_portfolio():
    position = Position(_build_listing())

    assert not hasattr(position, "participant_reference")
    assert not hasattr(position, "participant_identity")
    assert not hasattr(position, "point_in_time")


def test_position_does_not_expose_prohibited_ownership_context():
    position = Position(_build_listing())

    assert not hasattr(position, "orders")
    assert not hasattr(position, "trades")
    assert not hasattr(position, "market_data")
    assert not hasattr(position, "settlement")
    assert not hasattr(position, "risk")
    assert not hasattr(position, "performance")


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_position_does_not_support_ordering():
    with pytest.raises(TypeError):
        _ = Position(_build_listing()) < Position(_build_listing("MSFT"))


def test_position_equality_remains_intentionally_unresolved():
    listing = _build_listing()

    assert Position(listing) != Position(listing)


def test_position_does_not_infer_identity_from_listing():
    listing = _build_listing()

    assert Position(listing) != Position(listing)


def test_position_identity_is_absent():
    position = Position(_build_listing())

    assert not hasattr(position, "position_identity")


def test_position_preserves_listing_reference_when_mutated():
    position = Position(_build_listing())
    replacement_listing = _build_listing("MSFT")

    position.listing = replacement_listing

    assert position.listing is replacement_listing
