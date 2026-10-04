"""Broker-assigned identity of one execution reported by a broker.

BrokerExecutionId is an external fact: the identifier a broker reports for one
execution against an order. An order may have several executions, so this is
not an order identity. Northstar never assigns one, and it is distinct from both
ClientOrderIdentity and BrokerOrderId.

The value is opaque. No length, character set or format is assumed here.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidBrokerExecutionIdError(ValidationError):
    """Raised when a BrokerExecutionId value is invalid."""


def _normalize(identity: str) -> str:
    if identity is None:
        raise InvalidBrokerExecutionIdError("BrokerExecutionId cannot be None.")
    if not isinstance(identity, str):
        raise InvalidBrokerExecutionIdError("BrokerExecutionId must be a string.")
    normalized = identity.strip()
    if not normalized:
        raise InvalidBrokerExecutionIdError("BrokerExecutionId cannot be empty.")
    return normalized


@dataclass(frozen=True, slots=True)
class BrokerExecutionId:
    """Immutable broker-owned opaque identity of one execution.

    BrokerExecutionId has no independent business meaning beyond identifying
    one execution at one broker. Its format is intentionally not defined here.
    """

    identity: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _normalize(self.identity))

    def __str__(self) -> str:
        return self.identity

    def __repr__(self) -> str:
        return f"BrokerExecutionId(identity={self.identity!r})"
