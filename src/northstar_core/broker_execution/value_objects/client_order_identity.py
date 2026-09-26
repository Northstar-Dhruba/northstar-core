"""Northstar-owned identity of one order Northstar submits to a broker.

ClientOrderIdentity is the identity Northstar assigns to a broker order before
the broker has seen it, and the reference by which the order is later found at
the broker. It is Northstar's own fact, unlike BrokerOrderId, which the broker
assigns. The two are distinct types so one can never stand in for the other.

The value is opaque. How it is derived is an Application concern, and how a
broker spells a client order reference is an Infrastructure concern; nothing is
generated, parsed or length-checked here.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidClientOrderIdentityError(ValidationError):
    """Raised when a ClientOrderIdentity value is invalid."""


def _normalize(identity: str) -> str:
    if identity is None:
        raise InvalidClientOrderIdentityError("ClientOrderIdentity cannot be None.")
    if not isinstance(identity, str):
        raise InvalidClientOrderIdentityError("ClientOrderIdentity must be a string.")
    normalized = identity.strip()
    if not normalized:
        raise InvalidClientOrderIdentityError("ClientOrderIdentity cannot be empty.")
    return normalized


@dataclass(frozen=True, slots=True)
class ClientOrderIdentity:
    """Immutable Northstar-owned opaque identity of one broker order.

    ClientOrderIdentity has no independent business meaning beyond identifying
    one order Northstar submits. Its format is intentionally not defined here.
    """

    identity: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _normalize(self.identity))

    def __str__(self) -> str:
        return self.identity

    def __repr__(self) -> str:
        return f"ClientOrderIdentity(identity={self.identity!r})"
