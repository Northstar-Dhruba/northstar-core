"""Core Domain Exchange entity.

Exchange represents a trading venue. It owns venue identity and stable
intrinsic descriptive meaning while remaining independent of instrument
identity and listing-specific market participation.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode


class InvalidExchangeError(ValidationError):
    """Raised when an exchange violates intrinsic business rules."""


def _normalize_text(value: str, field_name: str) -> str:
    if value is None:
        raise InvalidExchangeError(f"Exchange {field_name} cannot be None.")
    if not isinstance(value, str):
        raise InvalidExchangeError(f"Exchange {field_name} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise InvalidExchangeError(f"Exchange {field_name} cannot be empty.")
    return normalized


def _validate_exchange_code(value: ExchangeCode) -> ExchangeCode:
    if value is None:
        raise InvalidExchangeError("Exchange code cannot be None.")
    if not isinstance(value, ExchangeCode):
        raise InvalidExchangeError("Exchange code must be an ExchangeCode value.")
    return value


def _normalize_description(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidExchangeError("Exchange description must be a string.")
    normalized = value.strip()
    if not normalized:
        raise InvalidExchangeError("Exchange description cannot be empty.")
    return normalized


@dataclass(slots=True, eq=False)
class Exchange:
    """Entity representing a trading venue.

    Exchange owns venue identity and stable intrinsic descriptive
    characteristics. Listing status, market participation, tradability, and
    operational configuration remain outside this entity boundary.

    Note:
        Custom equality and hashing are intentionally not defined. Until the
        Core Domain entity identity model is explicitly approved, Exchange
        uses Python object identity semantics.

        The approved architecture defines Exchange lifecycle conceptually but
        does not yet define a state representation or transition API. Lifecycle
        mechanics therefore remain deferred.
    """

    exchange_code: ExchangeCode
    name: str
    description: str | None = None

    def __post_init__(self) -> None:
        self.exchange_code = _validate_exchange_code(self.exchange_code)
        self.name = _normalize_text(self.name, "name")
        self.description = _normalize_description(self.description)

    def rename(self, name: str) -> None:
        """Update the intrinsic descriptive name of the venue."""

        self.name = _normalize_text(name, "name")

    def update_description(self, description: str | None) -> None:
        """Update stable intrinsic descriptive venue information."""

        self.description = _normalize_description(description)

    def __repr__(self) -> str:
        return (
            "Exchange("
            f"exchange_code={self.exchange_code!r}, "
            f"name={self.name!r}, "
            f"description={self.description!r}"
            ")"
        )
