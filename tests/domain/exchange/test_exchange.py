"""Reference contract test suite for the Exchange entity.

This suite defines the Northstar Core Domain entity contract.
"""

import pytest

from northstar_core.domain.exchange import Exchange, InvalidExchangeError
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    Currency,
    ExchangeCode,
    Money,
    Price,
)

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_exchange():
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")

    assert exchange.exchange_code == ExchangeCode("NASDAQ")
    assert exchange.name == "NASDAQ"
    assert exchange.description is None


def test_description_is_optional():
    exchange = Exchange(
        ExchangeCode("NASDAQ"),
        "NASDAQ",
        description="United States electronic stock exchange",
    )

    assert exchange.description == "United States electronic stock exchange"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none_exchange_code():
    with pytest.raises(InvalidExchangeError, match="code cannot be None"):
        Exchange(None, "NASDAQ")


def test_rejects_non_exchange_code_value():
    with pytest.raises(
        InvalidExchangeError,
        match="code must be an ExchangeCode value",
    ):
        Exchange("NASDAQ", "NASDAQ")


def test_rejects_empty_name():
    with pytest.raises(InvalidExchangeError, match="name cannot be empty"):
        Exchange(ExchangeCode("NASDAQ"), "")


def test_rejects_whitespace_only_name():
    with pytest.raises(InvalidExchangeError, match="name cannot be empty"):
        Exchange(ExchangeCode("NASDAQ"), "   ")


def test_rejects_invalid_description_type():
    with pytest.raises(InvalidExchangeError, match="description must be a string"):
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ", description=100)


def test_rejects_empty_description_string():
    with pytest.raises(InvalidExchangeError, match="description cannot be empty"):
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ", description="")


def test_invalid_exchange_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Exchange(None, "NASDAQ")


def test_invalid_exchange_error_is_a_value_error():
    with pytest.raises(ValueError):
        Exchange(None, "NASDAQ")


# ---------------------------------------------------------------------------
# Business Behavior
# ---------------------------------------------------------------------------


def test_rename_updates_only_the_exchange_name():
    exchange = Exchange(
        ExchangeCode("NASDAQ"),
        "NASDAQ",
        description="United States electronic stock exchange",
    )

    exchange.rename("Nasdaq Stock Market")

    assert exchange.name == "Nasdaq Stock Market"
    assert exchange.exchange_code == ExchangeCode("NASDAQ")
    assert exchange.description == "United States electronic stock exchange"


def test_update_description_updates_only_the_description():
    exchange = Exchange(
        ExchangeCode("NASDAQ"),
        "NASDAQ",
        description="United States electronic stock exchange",
    )

    exchange.update_description("Electronic equity trading venue")

    assert exchange.description == "Electronic equity trading venue"
    assert exchange.exchange_code == ExchangeCode("NASDAQ")
    assert exchange.name == "NASDAQ"


def test_update_description_can_remove_optional_description():
    exchange = Exchange(
        ExchangeCode("NASDAQ"),
        "NASDAQ",
        description="United States electronic stock exchange",
    )

    exchange.update_description(None)

    assert exchange.description is None


# ---------------------------------------------------------------------------
# Mutability
# ---------------------------------------------------------------------------


def test_rename_changes_business_state():
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")

    exchange.rename("Nasdaq Stock Market")

    assert exchange.name == "Nasdaq Stock Market"


def test_update_description_changes_business_state():
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")

    exchange.update_description("Electronic equity trading venue")

    assert exchange.description == "Electronic equity trading venue"


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def test_exchange_composes_exchange_code():
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")

    assert isinstance(exchange.exchange_code, ExchangeCode)


def test_exchange_does_not_expose_out_of_boundary_concepts():
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")

    assert not hasattr(exchange, "instrument")
    assert not hasattr(exchange, "listing")
    assert not hasattr(exchange, "currency")
    assert not hasattr(exchange, "price")
    assert not hasattr(exchange, "money")
    assert not hasattr(exchange, "listing_status")
    assert not hasattr(exchange, "market_participation")
    assert not hasattr(exchange, "tradability")


def test_exchange_does_not_compose_market_specific_value_objects():
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")

    assert not isinstance(exchange, Currency)
    assert not isinstance(exchange, Price)
    assert not isinstance(exchange, Money)


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_repr_contains_entity_name_code_and_name():
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")

    representation = repr(exchange)

    assert "Exchange" in representation
    assert "ExchangeCode" in representation
    assert "NASDAQ" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_description_may_be_none():
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ", description=None)

    assert exchange.description is None


def test_leading_and_trailing_whitespace_is_normalized():
    exchange = Exchange(
        ExchangeCode("NASDAQ"),
        "  NASDAQ  ",
        description="  United States electronic stock exchange  ",
    )

    assert exchange.name == "NASDAQ"
    assert exchange.description == "United States electronic stock exchange"


def test_exchange_code_remains_unchanged_after_rename():
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")

    exchange.rename("Nasdaq Stock Market")

    assert exchange.exchange_code == ExchangeCode("NASDAQ")


def test_description_update_does_not_affect_exchange_code():
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")

    exchange.update_description("Electronic equity trading venue")

    assert exchange.exchange_code == ExchangeCode("NASDAQ")
