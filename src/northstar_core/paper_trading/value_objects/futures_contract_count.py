"""Positive whole number of futures contracts in one simulated trade.

Futures trade in whole contracts, so a count is an exact integer rather than a
Decimal quantity. Quantity is deliberately not reused: it admits zero and
fractional magnitudes, and its arithmetic consults the ambient decimal context.

The count is unsigned. Trade direction is carried by OrderSide, and signed net
exposure belongs to FuturesPosition, so a count never says which way a trade
went.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidFuturesContractCountError(ValidationError):
    """Raised when a FuturesContractCount value is invalid."""


def _validate_value(value: int) -> int:
    if value is None:
        raise InvalidFuturesContractCountError("FuturesContractCount cannot be None.")
    # bool is an int subclass; True must not pass as one contract.
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidFuturesContractCountError("FuturesContractCount must be an integer.")
    if value < 1:
        raise InvalidFuturesContractCountError("FuturesContractCount must be greater than zero.")
    return value


@dataclass(frozen=True, slots=True, order=True)
class FuturesContractCount:
    """Immutable positive whole number of futures contracts.

    Only ``int`` is accepted. An integral Decimal such as ``Decimal("2")`` is
    rejected rather than converted, so the caller -- not this value -- owns any
    conversion from a decimal source.
    """

    value: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _validate_value(self.value))

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"FuturesContractCount(value={self.value!r})"
