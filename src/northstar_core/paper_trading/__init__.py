"""Paper trading bounded context package.

Paper trading simulates execution against observed market evidence. It models
no broker, no real-money execution, no leverage or margin, no commission or
slippage, no advanced order types, and no options. Futures paper values hold
whole-contract signed exposure only; futures economics and profit and loss are
deferred.

Every value here is immutable and derived from market observation, so a
simulated execution is reproducible: nothing reads a clock and nothing is
random. This package is deliberately independent of the legacy Orders, Trades
and Portfolio reference aggregates, which model listing identity through the
Listing entity rather than ListingReference.
"""

from .value_objects import (
    ExecutionIntent,
    FuturesContractCount,
    FuturesExecutionIntent,
    FuturesPaperFill,
    FuturesPaperOrder,
    FuturesPaperPortfolio,
    FuturesPosition,
    InvalidExecutionIntentError,
    InvalidFuturesContractCountError,
    InvalidFuturesExecutionIntentError,
    InvalidFuturesPaperFillError,
    InvalidFuturesPaperOrderError,
    InvalidFuturesPaperPortfolioError,
    InvalidFuturesPositionError,
    InvalidPaperFillError,
    InvalidPaperFillIdentityError,
    InvalidPaperOrderError,
    InvalidPaperOrderIdentityError,
    InvalidPaperPortfolioError,
    InvalidPaperPortfolioIdentityError,
    InvalidPositionError,
    OrderSide,
    PaperFill,
    PaperFillIdentity,
    PaperOrder,
    PaperOrderIdentity,
    PaperOrderStatus,
    PaperPortfolio,
    PaperPortfolioIdentity,
    Position,
)

__all__ = [
    "ExecutionIntent",
    "FuturesContractCount",
    "FuturesExecutionIntent",
    "FuturesPaperFill",
    "FuturesPaperOrder",
    "FuturesPaperPortfolio",
    "FuturesPosition",
    "InvalidExecutionIntentError",
    "InvalidFuturesContractCountError",
    "InvalidFuturesExecutionIntentError",
    "InvalidFuturesPaperFillError",
    "InvalidFuturesPaperOrderError",
    "InvalidFuturesPaperPortfolioError",
    "InvalidFuturesPositionError",
    "InvalidPaperFillError",
    "InvalidPaperFillIdentityError",
    "InvalidPaperOrderError",
    "InvalidPaperOrderIdentityError",
    "InvalidPaperPortfolioError",
    "InvalidPaperPortfolioIdentityError",
    "InvalidPositionError",
    "OrderSide",
    "PaperFill",
    "PaperFillIdentity",
    "PaperOrder",
    "PaperOrderIdentity",
    "PaperOrderStatus",
    "PaperPortfolio",
    "PaperPortfolioIdentity",
    "Position",
]
