"""Reference contract test suite for the Listing entity.

This suite defines the Northstar Core Domain entity contract.
"""

import pytest

from northstar_core.domain.exchange import Exchange
from northstar_core.domain.instrument import Instrument
from northstar_core.domain.listing import InvalidListingError, Listing
from northstar_core.domain.value_objects import ListingStatus, Tradability
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, ExchangeCode, Symbol

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_listing():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")
    currency = Currency("USD")
    listing_status = ListingStatus("Active")
    tradability = Tradability("Permitted")

    listing = Listing(instrument, exchange, currency, listing_status, tradability)

    assert listing.instrument is instrument
    assert listing.exchange is exchange
    assert listing.currency == currency
    assert listing.listing_status == listing_status
    assert listing.tradability == tradability
    assert listing.description is None


def test_description_is_optional():
    listing = Listing(
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        ListingStatus("Active"),
        Tradability("Permitted"),
        description="NASDAQ listing",
    )

    assert listing.description == "NASDAQ listing"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none_instrument():
    with pytest.raises(InvalidListingError, match="instrument cannot be None"):
        Listing(
            None,
            Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
            Currency("USD"),
            ListingStatus("Active"),
            Tradability("Permitted"),
        )


def test_rejects_none_exchange():
    with pytest.raises(InvalidListingError, match="exchange cannot be None"):
        Listing(
            Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
            None,
            Currency("USD"),
            ListingStatus("Active"),
            Tradability("Permitted"),
        )


def test_rejects_none_currency():
    with pytest.raises(InvalidListingError, match="currency cannot be None"):
        Listing(
            Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
            Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
            None,
            ListingStatus("Active"),
            Tradability("Permitted"),
        )


def test_rejects_none_listing_status():
    with pytest.raises(InvalidListingError, match="status cannot be None"):
        Listing(
            Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
            Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
            Currency("USD"),
            None,
            Tradability("Permitted"),
        )


def test_rejects_none_tradability():
    with pytest.raises(InvalidListingError, match="tradability cannot be None"):
        Listing(
            Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
            Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
            Currency("USD"),
            ListingStatus("Active"),
            None,
        )


def test_rejects_invalid_instrument_type():
    with pytest.raises(InvalidListingError, match="instrument must be an Instrument"):
        Listing(
            "AAPL",
            Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
            Currency("USD"),
            ListingStatus("Active"),
            Tradability("Permitted"),
        )


def test_rejects_invalid_exchange_type():
    with pytest.raises(InvalidListingError, match="exchange must be an Exchange"):
        Listing(
            Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
            "NASDAQ",
            Currency("USD"),
            ListingStatus("Active"),
            Tradability("Permitted"),
        )


def test_rejects_invalid_currency_type():
    with pytest.raises(InvalidListingError, match="currency must be a Currency"):
        Listing(
            Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
            Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
            "USD",
            ListingStatus("Active"),
            Tradability("Permitted"),
        )


def test_rejects_invalid_listing_status_type():
    with pytest.raises(
        InvalidListingError,
        match="status must be a ListingStatus value",
    ):
        Listing(
            Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
            Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
            Currency("USD"),
            "Active",
            Tradability("Permitted"),
        )


def test_rejects_invalid_tradability_type():
    with pytest.raises(
        InvalidListingError,
        match="tradability must be a Tradability value",
    ):
        Listing(
            Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
            Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
            Currency("USD"),
            ListingStatus("Active"),
            True,
        )


def test_rejects_invalid_description_type():
    with pytest.raises(InvalidListingError, match="description must be a string"):
        Listing(
            Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
            Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
            Currency("USD"),
            ListingStatus("Active"),
            Tradability("Permitted"),
            description=100,
        )


def test_rejects_empty_description():
    with pytest.raises(InvalidListingError, match="description cannot be empty"):
        Listing(
            Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
            Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
            Currency("USD"),
            ListingStatus("Active"),
            Tradability("Permitted"),
            description="",
        )


def test_invalid_listing_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Listing(
            None,
            Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
            Currency("USD"),
            ListingStatus("Active"),
            Tradability("Permitted"),
        )


def test_invalid_listing_error_is_a_value_error():
    with pytest.raises(ValueError):
        Listing(
            None,
            Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
            Currency("USD"),
            ListingStatus("Active"),
            Tradability("Permitted"),
        )


# ---------------------------------------------------------------------------
# Business Behavior
# ---------------------------------------------------------------------------


def test_update_status_replaces_only_listing_status():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")
    currency = Currency("USD")
    tradability = Tradability("Permitted")
    listing = Listing(
        instrument,
        exchange,
        currency,
        ListingStatus("Created"),
        tradability,
        description="NASDAQ listing",
    )
    updated_status = ListingStatus("Active")

    listing.update_status(updated_status)

    assert listing.listing_status is updated_status
    assert listing.instrument is instrument
    assert listing.exchange is exchange
    assert listing.currency == currency
    assert listing.tradability is tradability
    assert listing.description == "NASDAQ listing"


def test_update_tradability_replaces_only_tradability():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")
    currency = Currency("USD")
    listing_status = ListingStatus("Active")
    listing = Listing(
        instrument,
        exchange,
        currency,
        listing_status,
        Tradability("Not Permitted"),
        description="NASDAQ listing",
    )
    updated_tradability = Tradability("Permitted")

    listing.update_tradability(updated_tradability)

    assert listing.tradability is updated_tradability
    assert listing.instrument is instrument
    assert listing.exchange is exchange
    assert listing.currency == currency
    assert listing.listing_status is listing_status
    assert listing.description == "NASDAQ listing"


def test_update_description_updates_only_description():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")
    currency = Currency("USD")
    listing_status = ListingStatus("Active")
    tradability = Tradability("Permitted")
    listing = Listing(
        instrument,
        exchange,
        currency,
        listing_status,
        tradability,
        description="NASDAQ listing",
    )

    listing.update_description("Primary NASDAQ listing")

    assert listing.description == "Primary NASDAQ listing"
    assert listing.instrument is instrument
    assert listing.exchange is exchange
    assert listing.currency == currency
    assert listing.listing_status is listing_status
    assert listing.tradability is tradability


# ---------------------------------------------------------------------------
# Mutability
# ---------------------------------------------------------------------------


def test_update_status_changes_business_state():
    listing = Listing(
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        ListingStatus("Created"),
        Tradability("Not Permitted"),
    )

    listing.update_status(ListingStatus("Active"))

    assert listing.listing_status == ListingStatus("Active")


def test_update_tradability_changes_business_state():
    listing = Listing(
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        ListingStatus("Active"),
        Tradability("Not Permitted"),
    )

    listing.update_tradability(Tradability("Permitted"))

    assert listing.tradability == Tradability("Permitted")


def test_update_description_changes_business_state():
    listing = Listing(
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        ListingStatus("Active"),
        Tradability("Permitted"),
    )

    listing.update_description("Primary NASDAQ listing")

    assert listing.description == "Primary NASDAQ listing"


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def test_listing_composes_approved_business_concepts():
    listing = Listing(
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        ListingStatus("Active"),
        Tradability("Permitted"),
    )

    assert isinstance(listing.instrument, Instrument)
    assert isinstance(listing.exchange, Exchange)
    assert isinstance(listing.currency, Currency)
    assert isinstance(listing.listing_status, ListingStatus)
    assert isinstance(listing.tradability, Tradability)


def test_listing_does_not_expose_out_of_boundary_concepts():
    listing = Listing(
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        ListingStatus("Active"),
        Tradability("Permitted"),
    )

    assert not hasattr(listing, "exchange_code")
    assert not hasattr(listing, "price")
    assert not hasattr(listing, "money")
    assert not hasattr(listing, "market_data")
    assert not hasattr(listing, "order")
    assert not hasattr(listing, "trade")
    assert not hasattr(listing, "position")
    assert not hasattr(listing, "portfolio")


def test_exchange_remains_canonical_owner_of_exchange_code():
    listing = Listing(
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        ListingStatus("Active"),
        Tradability("Permitted"),
    )

    assert isinstance(listing.exchange.exchange_code, ExchangeCode)
    assert not hasattr(listing, "exchange_code")


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_repr_contains_entity_and_composed_business_values():
    listing = Listing(
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        ListingStatus("Active"),
        Tradability("Permitted"),
    )

    representation = repr(listing)

    assert "Listing" in representation
    assert "Instrument" in representation
    assert "Exchange" in representation
    assert "Currency" in representation
    assert "ListingStatus" in representation
    assert "Tradability" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_description_may_be_none():
    listing = Listing(
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        ListingStatus("Active"),
        Tradability("Permitted"),
        description=None,
    )

    assert listing.description is None


def test_leading_and_trailing_description_whitespace_is_normalized():
    listing = Listing(
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        ListingStatus("Active"),
        Tradability("Permitted"),
        description="  NASDAQ listing  ",
    )

    assert listing.description == "NASDAQ listing"


def test_updating_listing_status_does_not_modify_instrument():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")
    listing = Listing(
        instrument,
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        ListingStatus("Created"),
        Tradability("Not Permitted"),
    )

    listing.update_status(ListingStatus("Active"))

    assert listing.instrument is instrument


def test_updating_listing_status_does_not_modify_exchange():
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")
    listing = Listing(
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        exchange,
        Currency("USD"),
        ListingStatus("Created"),
        Tradability("Not Permitted"),
    )

    listing.update_status(ListingStatus("Active"))

    assert listing.exchange is exchange


def test_updating_tradability_does_not_modify_listing_status():
    listing_status = ListingStatus("Active")
    listing = Listing(
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        listing_status,
        Tradability("Not Permitted"),
    )

    listing.update_tradability(Tradability("Permitted"))

    assert listing.listing_status is listing_status


def test_updating_description_does_not_modify_composed_value_objects():
    currency = Currency("USD")
    listing_status = ListingStatus("Active")
    tradability = Tradability("Permitted")
    listing = Listing(
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        currency,
        listing_status,
        tradability,
    )

    listing.update_description("Primary NASDAQ listing")

    assert listing.currency is currency
    assert listing.listing_status is listing_status
    assert listing.tradability is tradability
