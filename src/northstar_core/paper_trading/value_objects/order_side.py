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

    BUY and SELL name trade direction only. What a SELL does to exposure --
    reduce or close a long, open or increase a short, or reverse long to short
    -- is decided by execution policy, not by this value. The equity Position
    is long-only, so equity paper trading never sells below zero.
    """

    BUY = "BUY"
    SELL = "SELL"
