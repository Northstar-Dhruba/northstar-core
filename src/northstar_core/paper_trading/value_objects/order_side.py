"""Paper-trading execution direction value object.

OrderSide expresses the direction of one simulated execution. It deliberately
has no HOLD member: HOLD is a recommendation outcome, not an execution
direction, and an advised HOLD must be incapable of producing an order at all.
Excluding it structurally means no runtime guard can be forgotten -- an
ExecutionIntent simply cannot represent a hold.

OrderSide carries no order type, time in force, routing, venue, leverage or
short-selling meaning.
"""

from __future__ import annotations

from enum import StrEnum


class OrderSide(StrEnum):
    """Closed vocabulary for the direction of one simulated execution.

    BUY increases a Position; SELL reduces one. Reduction below zero is not
    representable, because paper trading is long-only until a signed quantity
    concept is approved.
    """

    BUY = "BUY"
    SELL = "SELL"
