"""Core Domain Tradability value object.

Tradability represents Listing market-participation capability. It is
immutable, identity-free, and reusable within the Core Domain.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError

_TRADABILITY_VALUES = frozenset({"Permitted", "Not Permitted"})


class InvalidTradabilityError(ValidationError):
    """Raised when a Tradability value is invalid."""


def _normalize(value: str) -> str:
    if value is None:
        raise InvalidTradabilityError("Tradability cannot be None.")
    if not isinstance(value, str):
        raise InvalidTradabilityError("Tradability must be a string.")
    normalized = value.strip()
    if not normalized:
        raise InvalidTradabilityError("Tradability cannot be empty.")
    return normalized


def _validate(value: str) -> None:
    if value not in _TRADABILITY_VALUES:
        raise InvalidTradabilityError("Tradability is not part of the approved vocabulary.")


@dataclass(frozen=True, slots=True)
class Tradability:
    """Immutable value representing Listing market-participation capability.

    The approved vocabulary is Permitted and Not Permitted. Tradability has
    no independent identity and is constrained by ListingStatus without
    encoding that relationship here.
    """

    value: str

    def __post_init__(self) -> None:
        normalized = _normalize(self.value)
        _validate(normalized)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Tradability(value={self.value!r})"
