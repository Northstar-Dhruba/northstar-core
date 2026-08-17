"""Core Domain Listing entity.

Listing represents the market-specific manifestation of an Instrument on an
Exchange. It owns market participation context without redefining the
intrinsic meaning of either related entity.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.exchange import Exchange
from northstar_core.domain.instrument import Instrument
from northstar_core.domain.value_objects import ListingStatus, Tradability
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency


class InvalidListingError(ValidationError):
    """Raised when a listing violates approved business rules."""


def _validate_instrument(value: Instrument) -> Instrument:
    if value is None:
        raise InvalidListingError("Listing instrument cannot be None.")
    if not isinstance(value, Instrument):
        raise InvalidListingError("Listing instrument must be an Instrument entity.")
    return value


def _validate_exchange(value: Exchange) -> Exchange:
    if value is None:
        raise InvalidListingError("Listing exchange cannot be None.")
    if not isinstance(value, Exchange):
        raise InvalidListingError("Listing exchange must be an Exchange entity.")
    return value


def _validate_currency(value: Currency) -> Currency:
    if value is None:
        raise InvalidListingError("Listing currency cannot be None.")
    if not isinstance(value, Currency):
        raise InvalidListingError("Listing currency must be a Currency value.")
    return value


def _normalize_description(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidListingError("Listing description must be a string.")
    normalized = value.strip()
    if not normalized:
        raise InvalidListingError("Listing description cannot be empty.")
    return normalized


@dataclass(slots=True, eq=False)
class Listing:
    """Entity representing market-specific Instrument participation.

    Listing composes one Instrument, one Exchange, one trading Currency, one
    ListingStatus, and one Tradability. Exchange remains the canonical owner
    of ExchangeCode.

    Note:
        Custom equality and hashing are intentionally not defined. Until the
        Core Domain entity identity model is explicitly approved, Listing uses
        Python object identity semantics.

        Listing lifecycle is defined conceptually by the approved architecture,
        but lifecycle transition mechanics are intentionally deferred.
    """

    instrument: Instrument
    exchange: Exchange
    currency: Currency
    listing_status: ListingStatus
    tradability: Tradability
    description: str | None = None

    def __post_init__(self) -> None:
        self.instrument = _validate_instrument(self.instrument)
        self.exchange = _validate_exchange(self.exchange)
        self.currency = _validate_currency(self.currency)
        if self.listing_status is None:
            raise InvalidListingError("Listing status cannot be None.")
        if not isinstance(self.listing_status, ListingStatus):
            raise InvalidListingError("Listing status must be a ListingStatus value.")
        if self.tradability is None:
            raise InvalidListingError("Listing tradability cannot be None.")
        if not isinstance(self.tradability, Tradability):
            raise InvalidListingError("Listing tradability must be a Tradability value.")
        self.description = _normalize_description(self.description)

    def update_status(self, status: ListingStatus) -> None:
        """Replace the Listing lifecycle value object."""

        if not isinstance(status, ListingStatus):
            raise InvalidListingError("Listing status must be a ListingStatus value.")
        self.listing_status = status

    def update_tradability(self, tradability: Tradability) -> None:
        """Replace the Listing market-capability value object."""

        if not isinstance(tradability, Tradability):
            raise InvalidListingError("Listing tradability must be a Tradability value.")
        self.tradability = tradability

    def update_description(self, description: str | None) -> None:
        """Update stable market-specific descriptive characteristics."""

        self.description = _normalize_description(description)

    def __repr__(self) -> str:
        return (
            "Listing("
            f"instrument={self.instrument!r}, "
            f"exchange={self.exchange!r}, "
            f"currency={self.currency!r}, "
            f"listing_status={self.listing_status!r}, "
            f"tradability={self.tradability!r}, "
            f"description={self.description!r}"
            ")"
        )
