"""Core Domain Listing Status value object.

ListingStatus represents the lifecycle meaning of a Listing. It is immutable,
identity-free, and reusable within the Core Domain.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError

_LISTING_STATUS_VALUES = frozenset({"Created", "Active", "Suspended", "Delisted", "Retired"})


class InvalidListingStatusError(ValidationError):
    """Raised when a ListingStatus value is invalid."""


def _normalize(value: str) -> str:
    if value is None:
        raise InvalidListingStatusError("Listing Status cannot be None.")
    if not isinstance(value, str):
        raise InvalidListingStatusError("Listing Status must be a string.")
    normalized = value.strip()
    if not normalized:
        raise InvalidListingStatusError("Listing Status cannot be empty.")
    return normalized


def _validate(value: str) -> None:
    if value not in _LISTING_STATUS_VALUES:
        raise InvalidListingStatusError("Listing Status is not part of the approved vocabulary.")


@dataclass(frozen=True, slots=True)
class ListingStatus:
    """Immutable value representing Listing lifecycle meaning.

    The approved vocabulary is Created, Active, Suspended, Delisted, and
    Retired. ListingStatus has no independent identity and does not represent
    Tradability or any other market-participation capability.
    """

    value: str

    def __post_init__(self) -> None:
        normalized = _normalize(self.value)
        _validate(normalized)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"ListingStatus(value={self.value!r})"
