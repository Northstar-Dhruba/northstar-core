"""Market Data bounded context package."""

from .quote import InvalidQuoteError, Quote

__all__ = [
    "InvalidQuoteError",
    "Quote",
]
