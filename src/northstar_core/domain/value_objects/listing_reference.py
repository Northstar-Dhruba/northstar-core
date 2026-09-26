"""Listing identity association value object.

ListingReference preserves market-listed asset attribution by composing one
Symbol and one ExchangeCode. It does not own Listing or Listing lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, Symbol


class InvalidListingReferenceError(ValidationError):
    """Raised when a ListingReference value is invalid."""


def _validate_symbol(value: Symbol) -> Symbol:
    if value is None:
        raise InvalidListingReferenceError("ListingReference symbol cannot be None.")
    if not isinstance(value, Symbol):
        raise InvalidListingReferenceError("ListingReference symbol must be a Symbol value.")
    return value


def _validate_exchange_code(value: ExchangeCode) -> ExchangeCode:
    if value is None:
        raise InvalidListingReferenceError("ListingReference exchange code cannot be None.")
    if not isinstance(value, ExchangeCode):
        raise InvalidListingReferenceError(
            "ListingReference exchange code must be an ExchangeCode value."
        )
    return value


@dataclass(frozen=True, slots=True)
class ListingReference:
    """Immutable Core Domain Value Object for listing identity association.

    ListingReference identifies which market-listed asset an observation or
    analysis refers to. Listing identity is market-specific and derives from
    the relationship between one Instrument and one Exchange; ListingReference
    preserves exactly that association through the approved Symbol and
    ExchangeCode identity values.

    ListingReference has no independent identity and does not own Listing
    meaning or lifecycle. It deliberately excludes trading Currency, Listing
    Status, Tradability, descriptive attributes, provider identifiers, and any
    live or historical acquisition distinction. Currency remains factual price
    denomination carried by Price, not listing identity.
    """

    symbol: Symbol
    exchange_code: ExchangeCode

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _validate_symbol(self.symbol))
        object.__setattr__(self, "exchange_code", _validate_exchange_code(self.exchange_code))

    def __str__(self) -> str:
        return f"{self.symbol}@{self.exchange_code}"

    def __repr__(self) -> str:
        return f"ListingReference(symbol={self.symbol!r}, exchange_code={self.exchange_code!r})"
