# Changelog

All notable changes to northstar-core are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

## [0.4.0] - 2026-09-14

### Added

- Market Observation Context for factual, time-bound market evidence.
- Deterministic Asset Analysis Generator behavior.
- Structured Recommendation Explanation and Explanation Reason value objects.
- Real Market Intelligence support for interpreting acquired observations.
- Watchlist Intelligence support through reusable analysis-domain contracts.

### Engineering

- Preserved the frozen Domain architecture and Strategy recommendation policy.
- Added focused contract coverage for Alpha Domain behavior.

---

### Foundation – Measurement Family Completion

### Added

- `Quantity` value object in `foundation.value_objects`.
- `Percentage` value object in `foundation.value_objects`.
- `InvalidQuantityError` and `InvalidPercentageError` in `foundation.exceptions.validation`.
- Quantity and Percentage contract test suites at `tests/foundation/value_objects/test_quantity.py` and `tests/foundation/value_objects/test_percentage.py`.

### Engineering

- Completed the Measurement Family as an approved Foundation Value Object family.
- Established `Quantity` as the Measurement Family root.
- Established `Percentage` as the second approved Measurement family member.
- Extended the approved Foundation Value Object family beyond the Identity baseline.

### Documentation

- Updated the Reference Implementation Registry.
- Formalized the Measurement Family status as complete.

### Foundation – Financial Family Initiation

### Added

- `Currency` Value Object in `foundation.value_objects`.
- `InvalidCurrencyError` in `foundation.exceptions.validation`.
- Currency contract test suite at `tests/foundation/value_objects/test_currency.py`.

### Engineering

- Established `Currency` as the Financial Family Root.
- Introduced the Financial Family.
- Extended the Foundation Value Object Family.
- Validated structural denomination semantics independent of registry membership.

### Documentation

- Updated the Reference Implementation Registry.
- Updated Foundation Family status.

### Foundation – Financial Family Expansion

### Added

- `Price` Value Object in `foundation.value_objects`.
- `InvalidPriceError` in `foundation.exceptions.validation`.
- `CurrencyMismatchError` in `foundation.exceptions.validation`.
- Price contract test suite at `tests/foundation/value_objects/test_price.py`.

### Engineering

- Approved the first composed Foundation Value Object.
- Established the composed Financial Value Object implementation pattern.
- Extended the Financial Family.
- Validated currency-aware business operations.
- Validated composed value object contract testing.

### Documentation

- Updated Reference Implementation Registry.
- Updated Financial Family implementation status.

### Foundation – Financial Family Completion

### Added

- `Money` Value Object in `foundation.value_objects`.
- `InvalidMoneyError` in `foundation.exceptions.validation`.
- Money contract test suite at `tests/foundation/value_objects/test_money.py`.

### Engineering

- Completed the Financial Family.
- Approved `Money` as the Financial Family financial-state value object.
- Established the complete composed Financial Value Object pattern.
- Completed the Financial Family implementation.
- Validated composed Financial Value Object semantics.

### Documentation

- Updated Reference Implementation Registry.
- Updated Financial Family status.

### Foundation – Temporal Family and Foundation Completion

### Added

- `Timeframe` Value Object in `foundation.value_objects`.
- `InvalidTimeframeError` in `foundation.exceptions.validation`.
- Timeframe contract test suite at `tests/foundation/value_objects/test_timeframe.py`.

### Engineering

- Completed the Temporal Family.
- Approved `Timeframe` as the Temporal Family Root.
- Completed the Foundation package.
- Validated closed-vocabulary temporal semantics.
- Completed Foundation implementation and contract verification.

### Documentation

- Updated Reference Implementation Registry.
- Updated Foundation Family status.
- Updated Foundation completion status.

### Core Domain – Instrument

#### Added

- Instrument entity.
- InvalidInstrumentError.
- Instrument Reference Entity Contract Test Suite.

#### Engineering

- Established Instrument as the first Core Domain Entity.
- Established Instrument as the first approved Core Domain Reference Entity.
- Established the Core Domain Entity implementation pattern.
- Validated Instrument against ADR-005.
- Completed Instrument implementation and contract verification.

#### Documentation

- Added the Core Domain Reference Implementation Registry.
- Updated Core Domain implementation status.

### Core Domain – Exchange

#### Added

- Exchange entity.
- InvalidExchangeError.
- Exchange Reference Entity Contract Test Suite.

#### Engineering

- Established Exchange as the second approved Core Domain Entity.
- Established Exchange as the second approved Core Domain Reference Entity.
- Verified Exchange against ADR-005.
- Completed Exchange implementation and contract verification.
- Preserved the approved Instrument / Exchange / Listing boundaries.

#### Documentation

- Updated the Core Domain Reference Implementation Registry.
- Updated Core Domain implementation progress.

### Core Domain – Listing

#### Added

- Listing entity.
- InvalidListingError.
- Listing Reference Entity Contract Test Suite.

#### Engineering

- Established Listing as the third approved Core Domain Entity.
- Established Listing as the third approved Core Domain Reference Entity.
- Completed implementation using approved Core Domain Value Objects.
- Verified Listing against ADR-005 and ADR-006.
- Removed duplicated ExchangeCode ownership from Listing.
- Completed Listing implementation and contract verification.
- Completed implementation of the Core Domain Foundation.

#### Documentation

- Updated the Core Domain Reference Implementations Registry.
- Updated Core Domain Foundation implementation status.

### Foundation – PointInTime

#### Added

- PointInTime Foundation Value Object.
- InvalidPointInTimeError.
- Reference Foundation Value Object Contract Suite.

#### Engineering

- Established PointInTime as the Reference Temporal Foundation Value Object.
- Completed implementation using the approved ADR-007 architecture.
- Verified canonical UTC normalization.
- Verified deterministic value equality and hashing.
- Verified PointInTime complements Timeframe.
- Completed implementation and contract verification.

#### Documentation

- Updated the Foundation Reference Implementations Registry.
- Updated Foundation implementation status.

### Market Data – Quote

#### Added

- Quote Reference Market Observation
- InvalidQuoteError
- Reference Market Observation Contract Suite

#### Engineering

- Established Quote as the first approved Reference Market Observation.
- Implemented immutable Market Observation composition.
- Implemented Listing, PointInTime, and QuotedMarketState composition.
- Verified aggregate ownership boundaries.
- Verified value equality and hashing.
- Verified immutable observation semantics.
- Completed implementation and contract verification.

#### Documentation

- Completed Quote Design Specification.
- Completed Quoted Market State Design Specification.
- Completed Market Observation implementation documentation.

### Market Data – Tick

#### Added

- Tick Reference High-Frequency Point Market Observation
- TickState Tick-specific Value Object
- InvalidTickError
- InvalidTickStateError
- Reference High-Frequency Point Market Observation Contract Suite
- Reference High-Frequency Point Observation Value Object Contract Suite

#### Engineering

- Established Tick as the approved Reference High-Frequency Point Market Observation.
- Established TickState as the approved Tick-specific Value Object.
- Implemented immutable high-frequency point Market Observation composition.
- Implemented Listing, PointInTime, and TickState composition.
- Verified aggregate ownership boundaries.
- Verified immutable observation semantics.
- Verified value equality and hashing.
- Completed implementation and contract verification.

#### Documentation

- Completed Tick Design Specification.
- Completed TickState Design Specification.
- Completed Tick implementation documentation.

### Market Data – Order Book

#### Added

- OrderBook Reference Market-Depth Observation
- OrderBookState Order Book-specific Value Object
- InvalidOrderBookError
- InvalidOrderBookStateError
- Reference Market-Depth Observation Contract Suite
- Reference Market-Depth Observation Value Object Contract Suite

#### Engineering

- Established OrderBook as the approved Reference Market-Depth Observation.
- Established OrderBookState as the approved Order Book-specific Value Object.
- Implemented immutable market-depth observation composition.
- Implemented Listing, PointInTime, and OrderBookState composition.
- Verified aggregate ownership boundaries.
- Verified immutable observation semantics.
- Verified value equality and hashing.
- Completed implementation and contract verification.

#### Documentation

- Completed Order Book Design Specification.
- Completed OrderBookState Design Specification.
- Completed OrderBook implementation documentation.

### Orders

#### Added

Reference Aggregate Root

- Order

Supporting Orders Value Objects

- OrderStatus
- OrderIdentity

Supporting Core Domain Value Objects

- ParticipantIdentity
- ParticipantReference

Exceptions

- InvalidOrderError
- InvalidOrderStatusError
- InvalidOrderIdentityError
- InvalidParticipantIdentityError
- InvalidParticipantReferenceError

Reference Contract Suites

- Order Reference Aggregate Contract Suite
- OrderStatus Reference Lifecycle Value Object Contract Suite
- OrderIdentity Reference Aggregate Identity Value Object Contract Suite
- ParticipantIdentity Reference Aggregate Identity Value Object Contract Suite
- ParticipantReference Reference Identity Association Value Object Contract Suite

#### Engineering

- Established Order as the Reference Aggregate Root.
- Established OrderStatus as the Reference Lifecycle State Value Object.
- Established OrderIdentity as the Reference Aggregate Identity Value Object.
- Established ParticipantIdentity as the second Aggregate Identity reference implementation.
- Established ParticipantReference as the Reference Identity Association Value Object.
- Implemented identity-based aggregate equality.
- Implemented aggregate composition.
- Verified ownership boundaries.
- Verified aggregate consistency.
- Completed implementation and contract verification.

#### Documentation

- Completed Order Design Specification.
- Completed OrderStatus Design Specification.
- Completed Participant Design Specification.
- Completed ParticipantIdentity Design Specification.
- Completed ParticipantReference Design Specification.
- Completed Order Business Composition Review.

### Trades

#### Added

Reference Aggregate Root

- Trade

Supporting Trades Value Objects

- TradeIdentity

Supporting Core Domain Value Objects

- ParticipantIdentity
- ParticipantReference

Exceptions

- InvalidTradeError
- InvalidTradeIdentityError

Reference Contract Suites

- Trade Reference Aggregate Contract Suite
- TradeIdentity Reference Aggregate Identity Value Object Contract Suite

#### Engineering

- Established Trade as the Reference Immutable Aggregate Root.
- Established TradeIdentity as the third Aggregate Identity Value Object reference implementation.
- Reused ParticipantReference for participant attribution.
- Implemented immutable aggregate composition.
- Implemented identity-based aggregate equality.
- Verified aggregate ownership boundaries.
- Verified historical execution immutability.
- Completed implementation and contract verification.

#### Documentation

- Completed Trade Business Analysis.
- Completed Trade Design Specification.
- Completed TradeIdentity Business Analysis.
- Completed TradeIdentity Design Specification.

### Portfolio

#### Added

Reference Aggregate Root

- Portfolio

Supporting Portfolio Value Objects

- PortfolioIdentity

Supporting Portfolio Entity

- Position

Supporting Core Domain Value Objects

- ParticipantIdentity
- ParticipantReference

Exceptions

- InvalidPortfolioError
- InvalidPortfolioIdentityError
- InvalidPositionError

Reference Contract Suites

- Portfolio Reference Aggregate Contract Suite
- PortfolioIdentity Reference Aggregate Identity Value Object Contract Suite
- Position Reference Entity Contract Suite

#### Engineering

- Established Portfolio as the Reference Ownership Interpretation Aggregate Root.
- Established PortfolioIdentity as the fourth Aggregate Identity reference implementation.
- Established Position as the Reference Subordinate Entity.
- Implemented Portfolio-owned Position collection.
- Implemented duplicate Listing protection.
- Implemented identity-based aggregate equality.
- Verified aggregate consistency.
- Completed implementation and contract verification.

#### Documentation

- Completed Portfolio Business Analysis.
- Completed Portfolio Design Specification.
- Completed PortfolioIdentity Business Analysis.
- Completed PortfolioIdentity Design Specification.
- Completed Position Business Analysis.
- Completed Position Design Specification.
- Completed Portfolio Position Collection & Aggregate Consistency Review.

### Strategy

#### Added

Reference Aggregate Root

- Strategy

Supporting Strategy Value Objects

- StrategyIdentity

Exceptions

- InvalidStrategyError
- InvalidStrategyIdentityError

Reference Contract Suites

- Strategy Reference Aggregate Contract Suite
- StrategyIdentity Reference Aggregate Identity Value Object Contract Suite

#### Engineering

- Established Strategy as the Reference Decision Policy Aggregate Root.
- Established StrategyIdentity as the fifth Aggregate Identity reference implementation.
- Implemented identity-based aggregate equality.
- Implemented minimal Aggregate Root composition.
- Confirmed external consumption of Market Data, Portfolio, Trade, and Order contexts.
- Completed implementation and contract verification.

#### Documentation

- Completed Strategy Business Analysis.
- Completed Strategy Design Specification.
- Completed StrategyIdentity Business Analysis.
- Completed StrategyIdentity Design Specification.

---

## [0.2.1] — 2026-08-11

### Foundation – ExchangeCode Reference Value Object

### Added

- `ExchangeCode` value object in `foundation.value_objects`.
- `InvalidExchangeCodeError` in `foundation.exceptions.validation`.
- ExchangeCode contract test suite at `tests/foundation/value_objects/test_exchange_code.py`.

### Engineering

- ExchangeCode designated as Northstar Reference Value Object v1.0.
- Extended the Northstar Reference Value Object Family.
- Verified Reference-First Engineering workflow across multiple Value Objects.

### Documentation

- Updated Reference Implementation Registry.

---

## [0.2.0] — 2026-08-10

### Foundation – Symbol Reference Implementation

### Added

- `Symbol` value object in `foundation.value_objects`.
- `ValidationError` and `InvalidSymbolError` exception hierarchy in `foundation.exceptions.validation`.
- Reference contract test suite at `tests/foundation/value_objects/test_symbol.py`.

### Engineering

- Established Northstar Reference Value Object v1.0 (`Symbol`).
- Established Northstar Value Object Testing Standard v1.0.

### Documentation

- Added Reference Implementation Registry at `docs/engineering/registry/Reference-Implementations.md`.
- Updated ES-002 with the Official Reference Implementations section.

---

## [0.1.0] — 2026-08-10

### Project Zero

### Added

- Initial repository structure.
- Foundation package skeleton (`enums`, `exceptions`, `identifiers`, `protocols`, `result`, `value_objects`).
