"""Paper trading bounded context package.

Paper trading simulates execution against observed market evidence. It models
no broker, no real-money execution, no leverage or margin, no commission or
slippage, no advanced order types, and no futures or options.

Every value here is immutable and derived from market observation, so a
simulated execution is reproducible: nothing reads a clock and nothing is
random. This package is deliberately independent of the legacy Orders, Trades
and Portfolio reference aggregates, which model listing identity through the
Listing entity rather than ListingReference.
"""

from .value_objects import (
    ExecutionIntent,
    InvalidExecutionIntentError,
    InvalidPaperFillError,
    InvalidPaperFillIdentityError,
    InvalidPaperOrderError,
    InvalidPaperOrderIdentityError,
    InvalidPaperPortfolioIdentityError,
    InvalidPositionError,
    OrderSide,
    PaperFill,
    PaperFillIdentity,
    PaperOrder,
    PaperOrderIdentity,
    PaperOrderStatus,
    PaperPortfolioIdentity,
    Position,
)

__all__ = [
    "ExecutionIntent",
    "InvalidExecutionIntentError",
    "InvalidPaperFillError",
    "InvalidPaperFillIdentityError",
    "InvalidPaperOrderError",
    "InvalidPaperOrderIdentityError",
    "InvalidPaperPortfolioIdentityError",
    "InvalidPositionError",
    "OrderSide",
    "PaperFill",
    "PaperFillIdentity",
    "PaperOrder",
    "PaperOrderIdentity",
    "PaperOrderStatus",
    "PaperPortfolioIdentity",
    "Position",
]
