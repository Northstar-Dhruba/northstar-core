"""Trade-specific Value Objects for the Trades bounded context."""

from .trade_identity import InvalidTradeIdentityError, TradeIdentity

__all__ = [
    "InvalidTradeIdentityError",
    "TradeIdentity",
]
