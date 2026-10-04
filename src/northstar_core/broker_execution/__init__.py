"""Broker execution bounded context package.

Broker execution models orders Northstar asks a broker to execute and the facts
the broker reports back: order status, executions and positions. Unlike paper
trading, nothing here is simulated. Every status, execution and position is an
external fact recorded as reported, and Northstar never constructs one to stand
in for something the broker did not say.

Only a broker DEMO environment is representable: there is no value for
real-money execution. Broker-specific symbols, identifier formats, price
conventions and SDKs stay in Infrastructure; this package names contracts by
FuturesContract and quotations by QuoteValue only.

The package reuses the shared futures execution vocabulary -- FuturesContract,
OrderSide, FuturesContractCount, StrategyIdentity, PointInTime and QuoteValue --
but none of the paper-trading execution types, and paper trading does not
depend on it. Every value is immutable; nothing reads a clock, generates an
identifier or persists anything. Submission journals, idempotency and
reconciliation are Application and Infrastructure concerns.
"""

from .value_objects import (
    BrokerAccountReference,
    BrokerEnvironment,
    BrokerExecutionId,
    BrokerOrderId,
    BrokerOrderStatus,
    ClientOrderIdentity,
    FuturesBrokerExecution,
    FuturesBrokerExecutionIntent,
    FuturesBrokerOrder,
    FuturesBrokerOrderObservation,
    FuturesBrokerPosition,
    InvalidBrokerAccountReferenceError,
    InvalidBrokerExecutionIdError,
    InvalidBrokerOrderIdError,
    InvalidClientOrderIdentityError,
    InvalidFuturesBrokerExecutionError,
    InvalidFuturesBrokerExecutionIntentError,
    InvalidFuturesBrokerOrderError,
    InvalidFuturesBrokerOrderObservationError,
    InvalidFuturesBrokerPositionError,
)

__all__ = [
    "BrokerAccountReference",
    "BrokerEnvironment",
    "BrokerExecutionId",
    "BrokerOrderId",
    "BrokerOrderStatus",
    "ClientOrderIdentity",
    "FuturesBrokerExecution",
    "FuturesBrokerExecutionIntent",
    "FuturesBrokerOrder",
    "FuturesBrokerOrderObservation",
    "FuturesBrokerPosition",
    "InvalidBrokerAccountReferenceError",
    "InvalidBrokerExecutionIdError",
    "InvalidBrokerOrderIdError",
    "InvalidClientOrderIdentityError",
    "InvalidFuturesBrokerExecutionError",
    "InvalidFuturesBrokerExecutionIntentError",
    "InvalidFuturesBrokerOrderError",
    "InvalidFuturesBrokerOrderObservationError",
    "InvalidFuturesBrokerPositionError",
]
