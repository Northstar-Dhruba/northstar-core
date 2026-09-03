"""Order-specific lifecycle status value object.

OrderStatus preserves lifecycle meaning for one Order. It remains subordinate
to Order and does not define concrete lifecycle states or transitions.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidOrderStatusError(ValidationError):
    """Raised when an OrderStatus value is invalid."""


def _normalize(value: str) -> str:
    if value is None:
        raise InvalidOrderStatusError("OrderStatus lifecycle meaning cannot be None.")
    if not isinstance(value, str):
        raise InvalidOrderStatusError("OrderStatus lifecycle meaning must be a string.")

    normalized = value.strip()
    if not normalized:
        raise InvalidOrderStatusError("OrderStatus lifecycle meaning cannot be empty.")

    return normalized


@dataclass(frozen=True, slots=True)
class OrderStatus:
    """Immutable Order-specific Value Object for lifecycle meaning.

    OrderStatus has no independent identity and does not define a lifecycle
    vocabulary or transition rules. Those remain part of the approved Order
    lifecycle design.
    """

    lifecycle_meaning: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "lifecycle_meaning", _normalize(self.lifecycle_meaning))

    def __str__(self) -> str:
        return self.lifecycle_meaning

    def __repr__(self) -> str:
        return f"OrderStatus(lifecycle_meaning={self.lifecycle_meaning!r})"
