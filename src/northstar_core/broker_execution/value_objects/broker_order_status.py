"""Broker-reported status of one order, normalized to Northstar's vocabulary.

The status is what the broker says about an order it has seen, translated from
the broker's own terms by Infrastructure. It is deliberately small:

    WORKING    accepted and not yet complete; possibly partly filled
    FILLED     every requested contract executed
    CANCELLED  withdrawn or expired before completing; possibly partly filled
    REJECTED   refused; nothing executed

There is no CREATED or SUBMITTED member. Whether Northstar has prepared or
attempted a submission is Northstar's own journal state, not something a broker
reports. There is no ACKNOWLEDGED member either: an acknowledged order is simply
WORKING. And there is no PARTIALLY_FILLED member: a partial fill is a filled
count above zero on an order that is not FILLED, so a separate status would be
a second way to state one fact.
"""

from __future__ import annotations

from enum import StrEnum


class BrokerOrderStatus(StrEnum):
    """Closed vocabulary for the broker-reported status of one order."""

    WORKING = "WORKING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

    @property
    def is_terminal(self) -> bool:
        """Return whether the broker will report no further change to the order."""
        return self is not BrokerOrderStatus.WORKING
