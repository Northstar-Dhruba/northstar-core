"""Canonical exchange code value object.

Purpose:
    Represent the canonical identifier of an exchange or trading venue as an immutable domain value.

Invariants:
    - An ExchangeCode instance is always valid.
    - An ExchangeCode value is always normalized to uppercase.
    - An ExchangeCode value never contains whitespace and never exceeds the allowed length.

Examples:
    NYSE, NASDAQ, XNYS, NSE, BSE, HKEX
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import InvalidExchangeCodeError

_EXCHANGE_CODE_PATTERN = re.compile(r"^[A-Z0-9_]{2,16}$")


def _normalize(value: str) -> str:
    if value is None:
        raise InvalidExchangeCodeError("ExchangeCode cannot be None.")
    if not isinstance(value, str):
        raise InvalidExchangeCodeError("ExchangeCode must be a string.")
    normalized = value.strip().upper()
    if not normalized:
        raise InvalidExchangeCodeError("ExchangeCode cannot be empty.")
    return normalized


def _validate(value: str) -> None:
    if len(value) < 2:
        raise InvalidExchangeCodeError("ExchangeCode is too short.")
    if len(value) > 16:
        raise InvalidExchangeCodeError("ExchangeCode exceeds maximum length.")
    if any(char.isspace() for char in value):
        raise InvalidExchangeCodeError("ExchangeCode contains whitespace.")
    if not _EXCHANGE_CODE_PATTERN.fullmatch(value):
        raise InvalidExchangeCodeError("ExchangeCode contains invalid characters.")


@dataclass(frozen=True, slots=True, order=True)
class ExchangeCode:
    """Immutable representation of a canonical exchange identifier.

    Purpose:
        Represents the canonical identifier of an exchange or trading venue.

    Invariants:
        - The stored value is always valid.
        - The stored value is always normalized to uppercase.
        - The stored value does not contain whitespace and is within the maximum length.

    Examples:
        NYSE
        NASDAQ
        XNYS
        NSE
        BSE
        HKEX
    """

    value: str

    def __post_init__(self) -> None:
        normalized = _normalize(self.value)
        _validate(normalized)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"ExchangeCode(value={self.value!r})"
