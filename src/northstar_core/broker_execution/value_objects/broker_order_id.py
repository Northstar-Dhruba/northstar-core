"""Broker-assigned identity of one order at the broker.

BrokerOrderId is an external fact: the identifier a broker reports for an order
once it has accepted it. Northstar never assigns one. It is distinct from the
Northstar-owned ClientOrderIdentity, so the two cannot be interchanged.

The value is opaque. Brokers differ in how they spell order identifiers, so no
length, character set or format is assumed here.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidBrokerOrderIdError(ValidationError):
    """Raised when a BrokerOrderId value is invalid."""


def _normalize(identity: str) -> str:
    if identity is None:
        raise InvalidBrokerOrderIdError("BrokerOrderId cannot be None.")
    if not isinstance(identity, str):
        raise InvalidBrokerOrderIdError("BrokerOrderId must be a string.")
    normalized = identity.strip()
    if not normalized:
        raise InvalidBrokerOrderIdError("BrokerOrderId cannot be empty.")
    return normalized


@dataclass(frozen=True, slots=True)
class BrokerOrderId:
    """Immutable broker-owned opaque identity of one order.

    BrokerOrderId has no independent business meaning beyond identifying one
    order at one broker. Its format is intentionally not defined here.
    """

    identity: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _normalize(self.identity))

    def __str__(self) -> str:
        return self.identity

    def __repr__(self) -> str:
        return f"BrokerOrderId(identity={self.identity!r})"
