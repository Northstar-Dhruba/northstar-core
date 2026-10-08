"""The right one option contract grants its holder.

A CALL grants the right to buy the underlying at the strike, and a PUT grants
the right to sell it. The right is part of a contract's identity: two contracts
identical in product, expiry and strike are still different contracts when one
is a call and the other a put.

The vocabulary is Northstar's own. Exchanges and providers spell the right in
their own ways -- NSE and its data vendors use ``CE`` and ``PE`` -- and those
spellings are mapped to this vocabulary in Infrastructure. They are
deliberately not members here, so no venue's naming can become domain identity
by being passed in.

OptionRight carries no exercise style, settlement method, moneyness, position
direction or order direction. Buying or selling a contract is OrderSide's
concern, not the right's.
"""

from __future__ import annotations

from enum import StrEnum


class OptionRight(StrEnum):
    """Closed vocabulary for the right one option contract grants."""

    CALL = "CALL"
    PUT = "PUT"
