"""Recommendations bounded context package.

A recommendation here is an actionable trade setup, distinct from the research
assessment it may be derived from (``northstar_core.strategy``) and from any
simulated or demo execution that may act on it (``northstar_core.paper_trading``
and ``northstar_core.broker_execution``). Each instrument family has its own
sub-package; ``northstar_core.recommendations.futures`` is the first.

This parent package exports nothing itself. See ADR-017.
"""

__all__: list[str] = []
