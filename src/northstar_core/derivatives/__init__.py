"""Shared derivatives package.

Concepts here are common to every derivative family. They are deliberately
placed below Futures and Options so that neither family depends on the other:
an equity option has an expiration without any futures involvement, and a
futures contract has one without any options involvement.

This package depends only on Foundation. It must never import Futures or
Options.
"""

from .value_objects import (
    ExpirationDate,
    InvalidExpirationDateError,
    InvalidUnderlyingReferenceError,
    UnderlyingReference,
)

__all__ = [
    "ExpirationDate",
    "InvalidExpirationDateError",
    "InvalidUnderlyingReferenceError",
    "UnderlyingReference",
]
