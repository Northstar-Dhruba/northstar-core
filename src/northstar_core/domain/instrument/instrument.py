"""Core Domain Instrument entity.

Instrument represents the intrinsic tradable business concept. It owns only
intrinsic identity and descriptive business meaning and remains independent of
market-specific participation concerns.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Symbol


class InvalidInstrumentError(ValidationError):
    """Raised when an instrument violates intrinsic business rules."""


def _normalize_text(value: str, field_name: str) -> str:
    if value is None:
        raise InvalidInstrumentError(f"Instrument {field_name} cannot be None.")
    if not isinstance(value, str):
        raise InvalidInstrumentError(f"Instrument {field_name} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise InvalidInstrumentError(f"Instrument {field_name} cannot be empty.")
    return normalized


def _validate_symbol(value: Symbol) -> Symbol:
    if value is None:
        raise InvalidInstrumentError("Instrument symbol cannot be None.")
    if not isinstance(value, Symbol):
        raise InvalidInstrumentError("Instrument symbol must be a Symbol value.")
    return value


def _normalize_description(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidInstrumentError("Instrument description must be a string.")
    normalized = value.strip()
    if not normalized:
        raise InvalidInstrumentError("Instrument description cannot be empty.")
    return normalized


@dataclass(slots=True, eq=False)
class Instrument:
    """Entity representing an intrinsic tradable financial concept.

    Business identity is intrinsic and market-independent. Market-specific
    participation such as exchange context, denomination, listing status, and
    tradability is intentionally outside this entity boundary.

    Note:
        Custom equality and hashing are intentionally not defined. Until the
        Core Domain entity identity model is explicitly approved, Instrument
        uses Python object identity semantics.
    """

    symbol: Symbol
    name: str
    asset_class: str
    description: str | None = None

    def __post_init__(self) -> None:
        self.symbol = _validate_symbol(self.symbol)
        self.name = _normalize_text(self.name, "name")
        self.asset_class = _normalize_text(self.asset_class, "asset class")
        self.description = _normalize_description(self.description)

    def rename(self, name: str) -> None:
        """Update the intrinsic descriptive name."""

        self.name = _normalize_text(name, "name")

    def reclassify(self, asset_class: str) -> None:
        """Update the intrinsic asset classification."""

        self.asset_class = _normalize_text(asset_class, "asset class")

    def redescribe(self, description: str | None) -> None:
        """Update optional descriptive business metadata."""

        self.description = _normalize_description(description)

    def __repr__(self) -> str:
        return (
            "Instrument("
            f"symbol={self.symbol!r}, "
            f"name={self.name!r}, "
            f"asset_class={self.asset_class!r}, "
            f"description={self.description!r}"
            ")"
        )
