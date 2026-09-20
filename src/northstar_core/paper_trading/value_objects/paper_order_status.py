"""Paper-trading order result value object.

PaperOrderStatus records the terminal result of one simulated execution
attempt. A PaperOrder is created already resolved: it is an immutable record of
what a simulated execution did, not a workflow token that advances.

There is deliberately no OPEN, PENDING, PARTIALLY_FILLED, CANCELLED or EXPIRED
member. Those states only become meaningful once execution is asynchronous --
when an order rests at a venue, fills over time, or can be withdrawn. Simulated
execution resolves immediately against decision-time evidence, so introducing a
lifecycle now would model a delay that does not exist and would invite mutable
order state that nothing can yet update correctly.
"""

from __future__ import annotations

from enum import StrEnum


class PaperOrderStatus(StrEnum):
    """Closed vocabulary for the terminal result of one simulated execution.

    FILLED means the simulated execution produced a PaperFill for the full
    intended quantity. REJECTED means it produced none, and no Position may be
    derived from it.
    """

    FILLED = "FILLED"
    REJECTED = "REJECTED"
