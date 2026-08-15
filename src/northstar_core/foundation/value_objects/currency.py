"""Canonical currency code value object.

Purpose:
    Represent a normalized financial denomination code as an immutable domain value.

Note:
    Currency validates only the structural correctness of a denomination code.
    It does not validate ISO 4217 membership, cryptocurrency registry membership,
    legal tender status, exchange support, or market availability. Those
    responsibilities belong to higher-level domain services such as a Currency
    Registry. The Foundation Value Object exists to enforce structural
    correctness, not external authority.

Invariants:
    - A Currency instance is always valid.
    - A Currency value is always normalized to uppercase.
    - A Currency value never contains whitespace and always matches the approved structural rule.

Examples:
    USD, EUR, GBP, JPY, INR, BTC, ETH, SOL, USDT, USDC
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import InvalidCurrencyError

_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3,5}$")


def _normalize(value: str) -> str:
    if value is None:
        raise InvalidCurrencyError("Currency cannot be None.")
    if not isinstance(value, str):
        raise InvalidCurrencyError("Currency must be a string.")
    normalized = value.strip().upper()
    if not normalized:
        raise InvalidCurrencyError("Currency cannot be empty.")
    return normalized


def _validate(value: str) -> None:
    if len(value) < 3:
        raise InvalidCurrencyError("Currency is too short.")
    if len(value) > 5:
        raise InvalidCurrencyError("Currency exceeds maximum length.")
    if any(char.isspace() for char in value):
        raise InvalidCurrencyError("Currency contains whitespace.")
    if not _CURRENCY_PATTERN.fullmatch(value):
        raise InvalidCurrencyError("Currency contains invalid characters.")


@dataclass(frozen=True, slots=True, order=True)
class Currency:
    """Immutable representation of a canonical currency code.

    Purpose:
        Preserve a normalized financial denomination identifier as a domain value.

    Business Meaning:
        Currency represents a denomination identifier only. For example, USD
        represents the denomination identifier USD. It does not imply ISO
        recognition, legal tender status, exchange support, or registry
        membership. Those concepts belong outside the Foundation layer.

    Invariants:
        - The stored value is always valid.
        - The stored value is always normalized to uppercase.
        - The stored value does not contain whitespace and matches the approved currency pattern.

    Examples:
        USD, EUR, GBP, JPY, INR, BTC, ETH, SOL, USDT, USDC
    """

    value: str

    def __post_init__(self) -> None:
        normalized = _normalize(self.value)
        _validate(normalized)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Currency(value={self.value!r})"
