"""Canonical market symbol value object.

Purpose:
    Represent a normalized financial market symbol as an immutable domain value.

Invariants:
    - A Symbol instance is always valid.
    - A Symbol value is always normalized to uppercase.
    - A Symbol value never contains whitespace and never exceeds the allowed length.

Examples:
    AAPL, MSFT, RELIANCE, BTCUSDT, NIFTY50, BANKNIFTY26AUG25000CE
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import InvalidSymbolError


_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9._-]{1,32}$")


def _normalize(value: str) -> str:
    if value is None:
        raise InvalidSymbolError("Symbol cannot be None.")
    if not isinstance(value, str):
        raise InvalidSymbolError("Symbol must be a string.")
    normalized = value.strip().upper()
    if not normalized:
        raise InvalidSymbolError("Symbol cannot be empty.")
    return normalized


def _validate(value: str) -> None:
    if len(value) > 32:
        raise InvalidSymbolError("Symbol exceeds maximum length.")
    if any(char.isspace() for char in value):
        raise InvalidSymbolError("Symbol contains whitespace.")
    if not _SYMBOL_PATTERN.fullmatch(value):
        raise InvalidSymbolError("Symbol contains invalid characters.")


@dataclass(frozen=True, slots=True, order=True)
class Symbol:
    """Immutable representation of a canonical market symbol.

    Purpose:
        Preserve a normalized financial instrument identifier as a domain value.

    Invariants:
        - The stored value is always valid.
        - The stored value is always normalized to uppercase.
        - The stored value does not contain whitespace and is within the maximum length.

    Examples:
        AAPL, MSFT, RELIANCE, BTCUSDT, NIFTY50, BANKNIFTY26AUG25000CE
    """

    value: str

    def __post_init__(self) -> None:
        normalized = _normalize(self.value)
        _validate(normalized)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Symbol(value={self.value!r})"
