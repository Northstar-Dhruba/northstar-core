# Northstar Core

`northstar-core` is the framework-independent Domain library for the Northstar Intelligence platform. It owns business meaning, validation, immutable value objects, market-observation interpretation, and recommendation policy.

## Implemented in Alpha v0.4

- Foundation Value Objects for symbols, prices, quantities, currency, time, and related financial concepts.
- Core Domain entities including Instrument, Exchange, and Listing.
- Market observation concepts and typed observation context.
- Deterministic `AssetAnalysisGenerator` behavior.
- Strategy recommendation policy producing BUY, HOLD, or SELL.
- Structured `RecommendationExplanation` and `ExplanationReason` values.
- Market-data reference concepts such as quotes, ticks, order books, and OHLC bars.
- Contract-focused tests for the implemented Domain surface.

## Responsibilities

Northstar Core owns:

- Domain entities and Value Objects;
- Domain invariants and validation;
- market-observation interpretation;
- Strategy recommendation policy;
- recommendation explanation meaning.

## Non-Responsibilities

Northstar Core does not contain:

- HTTP or FastAPI;
- databases or persistence;
- external provider communication;
- Application workflow orchestration;
- authentication;
- React or UI code;
- scheduling, notifications, or execution integration.

## Architecture

Dependencies point inward toward Domain meaning. Core has no runtime dependencies and remains usable by Application and Infrastructure repositories through explicit contracts.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for setup, validation, and common workflows. Contribution expectations are documented in [CONTRIBUTING.md](CONTRIBUTING.md).

## Future Work

The following capabilities are planned or represented only as future Domain areas and are not Alpha product capabilities:

- confidence assessment;
- risk assessment;
- portfolio intelligence;
- research workspace;
- execution behavior;
- broader analytics and backtesting.
