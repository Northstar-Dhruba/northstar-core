"""Reference contract test suite for the Instrument entity.

This suite defines the Northstar Core Domain entity contract.
"""

import pytest

from northstar_core.domain.instrument import Instrument, InvalidInstrumentError
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, Money, Price, Symbol

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_instrument():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")

    assert instrument.symbol == Symbol("AAPL")
    assert instrument.name == "Apple Inc."
    assert instrument.asset_class == "Equity"
    assert instrument.description is None


def test_description_is_optional():
    instrument = Instrument(
        Symbol("AAPL"),
        "Apple Inc.",
        "Equity",
        description="Common stock",
    )

    assert instrument.description == "Common stock"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none_symbol():
    with pytest.raises(InvalidInstrumentError, match="symbol cannot be None"):
        Instrument(None, "Apple Inc.", "Equity")


def test_rejects_non_symbol_value():
    with pytest.raises(InvalidInstrumentError, match="symbol must be a Symbol value"):
        Instrument("AAPL", "Apple Inc.", "Equity")


def test_rejects_empty_name():
    with pytest.raises(InvalidInstrumentError, match="name cannot be empty"):
        Instrument(Symbol("AAPL"), "", "Equity")


def test_rejects_whitespace_only_name():
    with pytest.raises(InvalidInstrumentError, match="name cannot be empty"):
        Instrument(Symbol("AAPL"), "   ", "Equity")


def test_rejects_empty_asset_class():
    with pytest.raises(InvalidInstrumentError, match="asset class cannot be empty"):
        Instrument(Symbol("AAPL"), "Apple Inc.", "")


def test_rejects_whitespace_only_asset_class():
    with pytest.raises(InvalidInstrumentError, match="asset class cannot be empty"):
        Instrument(Symbol("AAPL"), "Apple Inc.", "   ")


def test_rejects_invalid_description_type():
    with pytest.raises(InvalidInstrumentError, match="description must be a string"):
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity", description=100)


def test_rejects_empty_description_string():
    with pytest.raises(InvalidInstrumentError, match="description cannot be empty"):
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity", description="")


def test_invalid_instrument_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Instrument(None, "Apple Inc.", "Equity")


def test_invalid_instrument_error_is_a_value_error():
    with pytest.raises(ValueError):
        Instrument(None, "Apple Inc.", "Equity")


# ---------------------------------------------------------------------------
# Business Behavior
# ---------------------------------------------------------------------------


def test_rename_updates_only_the_name():
    instrument = Instrument(
        Symbol("AAPL"),
        "Apple Inc.",
        "Equity",
        description="Common stock",
    )

    instrument.rename("Apple Corporation")

    assert instrument.name == "Apple Corporation"
    assert instrument.symbol == Symbol("AAPL")
    assert instrument.asset_class == "Equity"
    assert instrument.description == "Common stock"


def test_reclassify_updates_only_the_asset_class():
    instrument = Instrument(
        Symbol("AAPL"),
        "Apple Inc.",
        "Equity",
        description="Common stock",
    )

    instrument.reclassify("Common Equity")

    assert instrument.asset_class == "Common Equity"
    assert instrument.symbol == Symbol("AAPL")
    assert instrument.name == "Apple Inc."
    assert instrument.description == "Common stock"


def test_redescribe_updates_only_the_description():
    instrument = Instrument(
        Symbol("AAPL"),
        "Apple Inc.",
        "Equity",
        description="Common stock",
    )

    instrument.redescribe("Technology company equity")

    assert instrument.description == "Technology company equity"
    assert instrument.symbol == Symbol("AAPL")
    assert instrument.name == "Apple Inc."
    assert instrument.asset_class == "Equity"


def test_redescribe_can_remove_optional_description():
    instrument = Instrument(
        Symbol("AAPL"),
        "Apple Inc.",
        "Equity",
        description="Common stock",
    )

    instrument.redescribe(None)

    assert instrument.description is None


# ---------------------------------------------------------------------------
# Mutability
# ---------------------------------------------------------------------------


def test_rename_changes_business_state():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")

    instrument.rename("Apple Corporation")

    assert instrument.name == "Apple Corporation"


def test_reclassify_changes_business_state():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")

    instrument.reclassify("Common Equity")

    assert instrument.asset_class == "Common Equity"


def test_redescribe_changes_business_state():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")

    instrument.redescribe("Technology company equity")

    assert instrument.description == "Technology company equity"


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def test_instrument_composes_symbol():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")

    assert isinstance(instrument.symbol, Symbol)


def test_instrument_does_not_expose_market_specific_concepts():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")

    assert not hasattr(instrument, "exchange")
    assert not hasattr(instrument, "listing")
    assert not hasattr(instrument, "exchange_code")
    assert not hasattr(instrument, "currency")
    assert not hasattr(instrument, "price")
    assert not hasattr(instrument, "money")


def test_instrument_does_not_compose_market_specific_value_objects():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")

    assert not isinstance(instrument, Currency)
    assert not isinstance(instrument, Price)
    assert not isinstance(instrument, Money)


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_repr_contains_entity_name_and_business_values():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")

    representation = repr(instrument)

    assert "Instrument" in representation
    assert "Symbol" in representation
    assert "Apple Inc." in representation
    assert "Equity" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_description_may_be_none():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity", description=None)

    assert instrument.description is None


def test_leading_and_trailing_whitespace_is_normalized():
    instrument = Instrument(
        Symbol("AAPL"),
        "  Apple Inc.  ",
        "  Equity  ",
        description="  Common stock  ",
    )

    assert instrument.name == "Apple Inc."
    assert instrument.asset_class == "Equity"
    assert instrument.description == "Common stock"


def test_symbol_remains_unchanged_after_rename():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")

    instrument.rename("Apple Corporation")

    assert instrument.symbol == Symbol("AAPL")


def test_asset_class_change_does_not_affect_name():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")

    instrument.reclassify("Common Equity")

    assert instrument.name == "Apple Inc."


def test_description_change_does_not_affect_symbol():
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")

    instrument.redescribe("Technology company equity")

    assert instrument.symbol == Symbol("AAPL")
