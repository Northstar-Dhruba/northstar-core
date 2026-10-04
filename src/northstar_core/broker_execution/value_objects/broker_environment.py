"""Closed vocabulary of broker environments Northstar may execute against.

Only DEMO exists. A broker's demonstration environment executes against
simulated money on the broker's own systems, so every order, status, execution
and position it reports is an external fact rather than something Northstar
simulates -- but no real money moves.

LIVE is deliberately absent, as are PAPER, SANDBOX and TEST. Excluding LIVE
structurally means real-money execution cannot be represented by any broker
execution value at all: no runtime flag can be forgotten, because there is no
value to set it to. Adding real-money execution later is a deliberate change to
this vocabulary, not a configuration choice. Internal paper trading is a
separate package and is not a broker environment.
"""

from __future__ import annotations

from enum import StrEnum


class BrokerEnvironment(StrEnum):
    """Closed vocabulary for the broker environment an account belongs to.

    DEMO names a broker's demonstration environment: broker-operated execution
    against simulated funds.
    """

    DEMO = "DEMO"
