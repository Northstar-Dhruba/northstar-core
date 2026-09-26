"""Reference to the economic underlying a derivative derives its value from.

An underlying is the economic thing itself -- an index, a commodity, a rate --
not any product written on it. Several products routinely share one underlying:
a standard and a micro contract track the same index and differ only in their
specifications. That is exactly why the underlying can never identify a
product, and why this value exists separately from the product reference.

The code is a canonical internal vocabulary rather than any market's spelling.
It is deliberately not a provider symbol, not an exchange product code and not
a listing symbol, so no provider's naming can become domain identity by being
passed here.

An underlying is frequently not listed anywhere -- an index or a physical
commodity has no listing of its own -- which is why this is an opaque code and
not a market-listing reference.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError

_UNDERLYING_REFERENCE_PATTERN = re.compile(r"^[A-Z0-9_]{1,32}$")


class InvalidUnderlyingReferenceError(ValidationError):
    """Raised when an UnderlyingReference value is invalid."""


def _normalize(value: str) -> str:
    if value is None:
        raise InvalidUnderlyingReferenceError("UnderlyingReference cannot be None.")
    if not isinstance(value, str):
        raise InvalidUnderlyingReferenceError("UnderlyingReference must be a string.")

    normalized = value.strip().upper()
    if not normalized:
        raise InvalidUnderlyingReferenceError("UnderlyingReference cannot be empty.")
    if len(normalized) > 32:
        raise InvalidUnderlyingReferenceError("UnderlyingReference exceeds maximum length.")
    if not _UNDERLYING_REFERENCE_PATTERN.fullmatch(normalized):
        raise InvalidUnderlyingReferenceError(
            "UnderlyingReference must contain only uppercase letters, digits and underscores."
        )

    return normalized


@dataclass(frozen=True, slots=True, order=True)
class UnderlyingReference:
    """Immutable reference to one economic underlying.

    The stored value is uppercase, trimmed and restricted to letters, digits
    and underscores. The vocabulary is narrower than a market Symbol on
    purpose: this is a canonical code the domain chooses, not a string a
    provider hands over, so punctuation that only exists to satisfy some
    venue's formatting has no place in it.

    Examples: SP500, WTI, GOLD, NIFTY50.
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _normalize(self.value))

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"UnderlyingReference(value={self.value!r})"
