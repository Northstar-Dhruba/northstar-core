"""Canonical percentage value object.

Purpose:
    Represent a normalized percentage as an immutable domain value.

Invariants:
    - A Percentage instance is always valid.
    - A Percentage value is always normalized to a canonical Decimal form.
    - A Percentage value never represents a symbolic identifier and remains finite.

Examples:
    -25, 0, 12.5, 100, 150, 1000

Semantic Meaning:
    Stored value

        12.5

    represents

        12.5%

    and NOT

        0.125

    Conversion between percentage and fractional ratio is application logic,
    not the responsibility of the Percentage value object.

Note:
    Percentage represents a reusable general-purpose percentage measurement.
    It does not represent quantity, money, price, tax, allocation, or return.
    Those are higher-level domain concepts that may apply additional business rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from northstar_core.foundation.exceptions.validation import InvalidPercentageError
from northstar_core.foundation.value_objects._canonical_decimal import (
    canonical_decimal,
)


def _normalize(value: object) -> Decimal:
    return canonical_decimal(value, "Percentage", InvalidPercentageError)


def _validate(value: Decimal) -> None:
    """Validate Percentage business invariants."""
    return


@dataclass(frozen=True, slots=True, order=True)
class Percentage:
    """Immutable representation of a canonical percentage.

    Purpose:
        Preserve a normalized percentage as a domain value.

    Invariants:
        - The stored value is always valid.
        - The stored value is always normalized to a canonical Decimal form.
        - The stored value remains finite and does not represent a symbolic identifier.

    Examples:
        -25
        0
        12.5
        100
        150
        1000
    """

    value: Decimal

    def __post_init__(self) -> None:
        normalized = _normalize(self.value)
        _validate(normalized)
        object.__setattr__(self, "value", normalized)

    def __add__(self, other: object) -> Percentage:
        if isinstance(other, Percentage):
            return Percentage(self.value + other.value)
        return NotImplemented

    def __sub__(self, other: object) -> Percentage:
        if isinstance(other, Percentage):
            return Percentage(self.value - other.value)
        return NotImplemented

    def __mul__(self, other: object) -> Percentage:
        if isinstance(other, Decimal):
            result = self.value * other
            return Percentage(result)
        return NotImplemented

    def __truediv__(self, other: object) -> Percentage:
        if isinstance(other, Decimal):
            if other == 0:
                raise InvalidPercentageError("Percentage cannot be divided by zero.")
            return Percentage(self.value / other)
        return NotImplemented

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"Percentage(value={self.value!r})"
