# Portfolio Intelligence — Technical Development Guide

**Version:** 0.2.0  
**Status:** BASELINE — NORMATIVE where labeled  
**Last updated:** 2026-09-11  
**Authority:** This document is the canonical engineering reference for Portfolio Intelligence where a section is labeled **Status: NORMATIVE**.  
**Supersedes:** Version 0.1.0 dated 2026-09-09  
**Integrated amendments:** Django/DRF application architecture; Apache ECharts frontend; multi-symbol market-bar retrieval; provider-pluggable yfinance/Alpaca boundary

---

## Table of Contents

1. [Purpose and Authority](#1-purpose-and-authority)
2. [Product Definition and Engineering Principles](#2-product-definition-and-engineering-principles)
3. [Scope and Release Boundaries](#3-scope-and-release-boundaries)
4. [System Architecture](#4-system-architecture)
5. [Repository Structure and Dependency Rules](#5-repository-structure-and-dependency-rules)
6. [Technology Baseline](#6-technology-baseline)
7. [Coding and Design Standards](#7-coding-and-design-standards)
8. [Core Domain Model and Data Contracts](#8-core-domain-model-and-data-contracts)
9. [Market Data Rules](#9-market-data-rules)
10. [Portfolio Accounting Rules](#10-portfolio-accounting-rules)
11. [Mathematical and Analytical Definitions](#11-mathematical-and-analytical-definitions)
12. [Portfolio Optimization](#12-portfolio-optimization)
13. [Rebalancing](#13-rebalancing)
14. [Backtesting and Anti-Look-Ahead Rules](#14-backtesting-and-anti-look-ahead-rules)
15. [Application API Contract](#15-application-api-contract)
16. [Frontend Contract](#16-frontend-contract)
17. [Asynchronous Work and Reproducibility](#17-asynchronous-work-and-reproducibility)
18. [AI Insight Layer](#18-ai-insight-layer)
19. [Testing Strategy](#19-testing-strategy)
20. [Observability, Provenance, and Auditability](#20-observability-provenance-and-auditability)
21. [Security, Privacy, and Product Positioning](#21-security-privacy-and-product-positioning)
22. [Performance and Reliability](#22-performance-and-reliability)
23. [MVP Acceptance Criteria](#23-mvp-acceptance-criteria)
24. [Phased Implementation Order](#24-phased-implementation-order)
25. [Change Control and Amendments](#25-change-control-and-amendments)
26. [Deferred Scope](#26-deferred-scope)
27. [Normative Constants](#27-normative-constants)

---

# 1. Purpose and Authority

**Status: NORMATIVE**

This document is the canonical engineering reference for Portfolio Intelligence. It defines the product's architectural boundaries, analytical formulas, data contracts, software-engineering standards, backtesting rules, testing requirements, release gates, and phased implementation order.

Where this guide and implementation code disagree, one of two things MUST happen:

1. the code MUST be changed to conform to this guide; or
2. this guide MUST be explicitly amended before intentionally changing the required behavior.

Implementation convenience is not sufficient justification for silently deviating from a NORMATIVE rule.

The guide exists to prevent architectural drift, mathematical drift, hidden analytical assumptions, inconsistent AI-generated code, and false confidence from tests that validate implementation details without validating analytical behavior.

Modules implementing a NORMATIVE rule SHOULD reference the applicable guide section in their module or class documentation when the relationship is not obvious.

---

# 2. Product Definition and Engineering Principles

## 2.1 Product definition

**Status: NORMATIVE**

Portfolio Intelligence is an investment analytics and decision-support platform designed to help an everyday investor answer five questions:

1. How is my portfolio performing?
2. What risks am I taking?
3. Am I actually diversified?
4. How would alternative allocations or rebalancing rules have behaved historically?
5. How would a defined investment strategy have performed under explicit historical assumptions?

The product is a research, analysis, simulation, and educational tool. It is not a brokerage, trade-execution system, fiduciary adviser, or autonomous investment manager.

## 2.2 Primary engineering principle

**Status: NORMATIVE**

The system SHALL follow this hierarchy:

```text
DATA
  ↓
DETERMINISTIC ANALYTICS
  ↓
STRUCTURED RESULTS
  ↓
EXPLANATION / VISUALIZATION
  ↓
DECISION SUPPORT
```

The quantitative engine is authoritative for calculations. The frontend displays results. The future AI layer explains deterministic results. No presentation layer or language model may independently invent a portfolio metric that is defined by the quantitative engine.

## 2.3 Simple interface, sophisticated engine

**Status: NORMATIVE**

The product MAY simplify the presentation of quantitative concepts, but MUST NOT simplify analytical implementation by using mathematically incorrect shortcuts without explicit labeling.

A user should not need quantitative-finance expertise to use the product. A technical reviewer should nevertheless be able to trace every displayed metric to documented code, data, assumptions, and tests.

## 2.4 Explainability

**Status: NORMATIVE**

Every derived result exposed through the API MUST be reproducible from identifiable inputs and assumptions. At minimum, analytical responses MUST make available:

- analysis period;
- data end date / `as_of_date`;
- price convention used;
- benchmark, when applicable;
- annualization factor, when applicable;
- risk-free or minimum-acceptable-return assumption, when applicable;
- data provider/source;
- engine version;
- warnings or insufficient-data conditions.

---

# 3. Scope and Release Boundaries

## 3.1 Supported MVP assets

**Status: NORMATIVE**

The public MVP supports:

- U.S.-listed common stocks;
- U.S.-listed ETFs;
- USD cash.

The MVP base currency is USD only.

## 3.2 Supported MVP capabilities

**Status: NORMATIVE**

The public MVP SHALL support:

### Portfolio management

- create and rename portfolios;
- record deposits and withdrawals;
- record buys and sells;
- optionally record cash dividends;
- import a documented CSV transaction format;
- derive holdings from the transaction ledger;
- select a benchmark.

### Market-data exploration

- accept a user-entered list of ticker symbols;
- normalize, validate, and resolve those symbols to internal assets;
- retrieve daily OHLCV bars for all valid symbols in one request;
- use yfinance as the credential-free default development/MVP provider;
- permit Alpaca and future providers through a common provider contract;
- display price and volume history with Apache ECharts;
- disclose the provider, retrieval time, date coverage, and per-symbol warnings.

### Portfolio analytics

- current market value;
- gain/loss where cost-basis information is available;
- time-weighted portfolio return;
- cumulative return;
- CAGR / annualized geometric return;
- annualized volatility;
- Sharpe ratio;
- Sortino ratio;
- maximum drawdown;
- beta;
- correlation matrix;
- current asset allocation;
- concentration measures;
- rolling returns.

### Allocation and optimization

- current allocation;
- equal-weight allocation;
- minimum-variance allocation;
- maximum-Sharpe allocation;
- efficient frontier;
- configurable long-only weight constraints.

### Rebalancing

- target weights;
- drift calculation;
- simulated rebalance trades;
- scheduled rebalancing comparison;
- drift-threshold rebalancing comparison.

### Backtesting

- buy-and-hold strategy;
- moving-average strategy;
- momentum strategy;
- explicit transaction costs;
- explicit slippage assumption;
- benchmark comparison;
- equity curve;
- drawdown series;
- trade history;
- standard performance metrics.

## 3.3 Explicit non-goals for MVP

**Status: NORMATIVE**

The following are excluded from the public MVP and MUST NOT be introduced before the relevant phase unless this guide is amended:

- live brokerage connectivity;
- live trade execution;
- autonomous trading;
- personalized buy/sell recommendations;
- options;
- futures;
- crypto assets;
- margin;
- short selling;
- leverage;
- tax-loss harvesting;
- wash-sale accounting;
- tax-lot optimization;
- retirement planning;
- multi-currency portfolios;
- social trading;
- financial-news aggregation;
- sentiment trading;
- free-form user-authored strategy code;
- machine-learning stock selection;
- Monte Carlo planning;
- full corporate-action accounting beyond the explicitly documented MVP treatment.

## 3.4 Release definitions

**Status: NORMATIVE**

- **v0.1.0 — Portfolio Analytics:** deterministic market-data normalization, ledger-derived holdings, portfolio performance/risk analytics, API surface, and a usable analytics UI.
- **v0.2.0 — Portfolio Optimization:** efficient frontier, minimum variance, maximum Sharpe, allocation comparison, and rebalance simulation.
- **v0.3.0 — Public MVP / Strategy Lab:** backtesting engine, initial strategies, transaction-cost modeling, strategy comparison UI, documentation, sample data, and reproducible demo workflows.
- **v0.4.0 — AI Portfolio Analyst:** grounded natural-language interpretation of structured analytical results. This release is post-MVP.

---

# 4. System Architecture

## 4.1 High-level architecture

**Status: NORMATIVE**

```text
┌──────────────────────────────────────────┐
│ React + TypeScript + Tailwind + ECharts  │
│ Presentation and interaction only       │
└───────────────────┬──────────────────────┘
                    │ REST / JSON
                    ▼
┌──────────────────────────────────────────┐
│ Django + Django REST Framework           │
│ API, services, persistence, auth         │
└──────────────┬───────────────┬───────────┘
               │               │
               ▼               ▼
┌──────────────────────┐  ┌──────────────────────┐
│ Portfolio Engine     │  │ Infrastructure       │
│ Pure quantitative   │  │ DB / cache / data   │
│ Python package       │  │ providers / Celery   │
└──────────────┬───────┘  └──────────┬───────────┘
               │                     │
               └──────────┬──────────┘
                          ▼
                 PostgreSQL / Redis
```

## 4.2 Quantitative-engine boundary

**Status: NORMATIVE**

The `portfolio_engine` package is a pure analytical library.

It MUST NOT import or depend on:

- Django;
- Django REST Framework;
- Django ORM models or migrations;
- Redis;
- Celery;
- HTTP clients;
- frontend code;
- application authentication state;
- database sessions;
- ORM entities.

It MAY depend on numerical and standard-library packages such as:

- NumPy;
- pandas;
- SciPy;
- Python standard library.

The application layer MAY import the quantitative engine. The quantitative engine MUST NOT import the application layer.

## 4.3 Application-layer responsibilities

**Status: NORMATIVE**

The Django application owns:

- URL routing and HTTP request/response handling;
- Django REST Framework serializer validation;
- authentication context;
- authorization to a user's portfolios;
- transaction persistence through the Django ORM;
- application-service orchestration;
- market-data adapter orchestration;
- caching;
- asynchronous run orchestration;
- mapping engine errors into stable API errors;
- serialization of analytical results.

DRF views/viewsets MUST remain thin. They MUST validate and authorize the request, call an application service, and serialize the result. Views, serializers, model methods, signals, and admin classes MUST NOT contain portfolio formulas, direct optimization logic, provider-specific normalization, or backtesting calculations.

Application workflows that mutate more than one persisted record MUST define their atomic boundary with `transaction.atomic()`. Django signals MUST NOT be used as an implicit substitute for explicit application-service orchestration.

## 4.4 Infrastructure boundary

**Status: NORMATIVE**

External systems SHALL be accessed through explicit adapters. Django ORM access SHALL be encapsulated by application services plus domain-specific QuerySet/manager methods where reuse or scoping requires it. A repository wrapper around every Django model is not required and MUST NOT be introduced without a concrete testability or architectural need.

Required abstractions include:

- market-data provider;
- cache interface;
- background-job dispatcher when asynchronous execution is enabled.

Provider selection MUST occur through configuration and/or an explicit server-side allowlist. Neither a DRF view nor the React application may import, instantiate, or special-case yfinance, Alpaca, or another provider.

---

# 5. Repository Structure and Dependency Rules

## 5.1 Repository layout

**Status: NORMATIVE**

```text
portfolio-intelligence/
│
├── README.md
├── LICENSE
├── docker-compose.yml
├── .env.example
├── Makefile
│
├── docs/
│   ├── dev-guide.md
│   ├── architecture.md
│   ├── analytics-methodology.md
│   ├── api-design.md
│   ├── data-model.md
│   └── amendments/
│
├── backend/
│   ├── pyproject.toml
│   ├── manage.py
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── local.py
│   │   │   ├── test.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── celery.py
│   ├── apps/
│   │   ├── accounts/
│   │   ├── assets/
│   │   ├── market_data/
│   │   │   ├── api/
│   │   │   ├── providers/
│   │   │   ├── services/
│   │   │   └── tasks.py
│   │   ├── portfolios/
│   │   ├── analytics/
│   │   ├── optimization/
│   │   └── backtesting/
│   ├── portfolio_engine/
│   │   ├── contracts/
│   │   ├── performance/
│   │   ├── portfolio/
│   │   ├── risk/
│   │   ├── optimization/
│   │   ├── rebalancing/
│   │   ├── backtesting/
│   │   └── strategies/
│   └── tests/
│       ├── unit/
│       ├── property/
│       ├── integration/
│       ├── validation/
│       └── architecture/
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/
│   │   └── types/
│   └── tests/
│
├── sample_data/
└── scripts/
```

## 5.2 Dependency direction

**Status: NORMATIVE**

Allowed dependency direction:

```text
frontend
   ↓ HTTP
DRF views / serializers
   ↓
application services
   ↓              ↘
Django ORM         portfolio_engine
   ↓
provider adapters / infrastructure
```

Forbidden dependencies include:

- model -> DRF view or serializer;
- provider adapter -> DRF view;
- `portfolio_engine` -> application service;
- `portfolio_engine` -> Django ORM model;
- `portfolio_engine` -> Django settings;
- frontend -> database;
- frontend -> market-data provider directly.

Architecture tests SHOULD enforce the most important dependency rules.

---

# 6. Technology Baseline

**Status: NORMATIVE**

The baseline stack is:

### Backend

- Python 3.12;
- Django 5.2 LTS;
- Django REST Framework;
- Django ORM and Django migrations;
- `django-filter` where resource filtering is exposed;
- `drf-spectacular` for the OpenAPI contract;
- PostgreSQL;
- Redis when caching or distributed work requires it;
- Celery when asynchronous heavy jobs are enabled;
- yfinance as the default credential-free market-data adapter;
- Alpaca's maintained Python SDK as an optional credentialed adapter;
- NumPy;
- pandas;
- SciPy;
- pytest;
- Hypothesis for property-based tests;
- Ruff;
- mypy.

### Frontend

- React;
- TypeScript with strict mode;
- Vite;
- Tailwind CSS;
- TanStack Query;
- React Router;
- Apache ECharts;
- Vitest;
- Playwright.

### Platform

- Docker Compose for local development;
- GitHub Actions for CI;
- lockfiles MUST be committed;
- runtime versions MUST be pinned in repository configuration.

Specific package patch/minor versions are controlled by lockfiles, not by this guide.

---

# 7. Coding and Design Standards

## 7.1 Python standards

**Status: NORMATIVE**

- New Python code MUST be type annotated.
- `mypy` MUST run in CI for the backend package set chosen by the project configuration.
- Ruff MUST enforce formatting and linting.
- Public engine functions MUST have docstrings describing units, assumptions, input shape, return shape, and exceptional conditions where those are not obvious.
- Functions implementing mathematical definitions SHOULD remain small and side-effect free.
- Pure calculations MUST NOT read environment variables, databases, clocks, network state, or global mutable application state.
- Domain enums MUST be explicit enums rather than magic strings inside business logic.
- Decimal money values MUST NOT be silently converted to binary floats inside persistence/business-ledger logic.
- NumPy/pandas analytical arrays SHALL use `float64` unless a documented reason requires another dtype.

## 7.2 TypeScript standards

**Status: NORMATIVE**

- TypeScript strict mode MUST remain enabled.
- API payload types MUST originate from a generated or explicitly maintained API contract; components MUST NOT repeatedly redefine response shapes.
- Calculation logic that is authoritative in Python MUST NOT be independently reimplemented in React except formatting-only transformations.
- Server state SHOULD be handled through TanStack Query rather than duplicated global state.
- Financial numbers MUST retain raw numeric values until formatting at the presentation boundary.

## 7.3 Naming

**Status: NORMATIVE**

Names MUST communicate units and meaning when ambiguity is possible.

Prefer:

- `annualized_volatility`
- `risk_free_rate_annual`
- `target_weight`
- `trade_notional_usd`

Avoid:

- `vol`
- `rate`
- `value2`
- `result_final`

## 7.4 No hidden assumptions

**Status: NORMATIVE**

Defaults that affect analytical results MUST be centralized, documented, and included in result metadata where material. Examples include:

- trading days per year;
- risk-free rate;
- minimum acceptable return;
- transaction-cost percentage;
- slippage percentage;
- minimum observation counts;
- optimization weight tolerance.

## 7.5 Django and DRF standards

**Status: NORMATIVE**

- Django models define persistence shape and local invariants; they MUST NOT orchestrate network calls or quantitative workflows.
- Cross-model and external-I/O workflows belong in explicit application services.
- Reusable query scoping belongs in typed custom `QuerySet`/manager methods.
- DRF serializers validate transport input and render transport output; they MUST NOT become the domain-service layer.
- DRF views/viewsets MUST select the authenticated scope before retrieving user-owned objects.
- Writes spanning multiple records MUST use explicit `transaction.atomic()` boundaries.
- Django signals SHOULD be limited to truly decoupled framework events. Financial ledger, market-data, and analytical workflows MUST NOT rely on hidden signal chains.
- Migrations MUST be deterministic, reviewed, reversible where practical, and runnable without network access.
- Application startup and `AppConfig.ready()` MUST NOT perform database or provider calls.
- Settings MUST be environment-driven, validated at startup, and separated into base/local/test/production modules.
- Celery tasks receive primitive identifiers and serializable inputs, then re-load current state inside the task; ORM instances MUST NOT be placed on the queue.
- `select_related`, `prefetch_related`, annotations, and query-count tests SHOULD be used where list endpoints would otherwise create N+1 queries.

---

# 8. Core Domain Model and Data Contracts

## 8.1 Identifiers and time

**Status: NORMATIVE**

- Primary application entities SHALL use UUID identifiers.
- Persisted timestamps SHALL be timezone-aware UTC.
- Daily market bars SHALL use an exchange trading date rather than a timestamp.
- The MVP supports USD as the only portfolio base currency.

## 8.2 Asset

**Status: NORMATIVE**

An asset record contains at minimum:

```text
id
symbol              canonical display symbol
name
asset_type        STOCK | ETF
exchange
currency          USD for MVP
is_active
created_at
updated_at
```

A display ticker is not a sufficient global identity. Internal calculations SHALL use `asset_id` after asset resolution.

Provider-specific identifiers SHALL be stored separately rather than added as one mutable column on `Asset`:

```text
AssetProviderSymbol
  id
  asset_id
  provider            YFINANCE | ALPACA | CSV | MOCK | future registered value
  provider_symbol
  is_primary
  verified_at
```

`(provider, provider_symbol)` MUST be unique. A provider adapter receives resolved provider symbols and returns results keyed back to internal `asset_id`. A ticker entered by a user MUST be resolved before it is used as an analytical identity.

## 8.3 PriceBar

**Status: NORMATIVE**

The canonical daily price-bar contract contains:

```text
asset_id
trade_date
open
high
low
close
adjusted_close
volume
source
retrieved_at
```

Rules:

- prices MUST be positive when present;
- `high >= low`;
- raw `open` and `close` SHOULD fall within `[low, high]` when all values are supplied;
- volume MUST be non-negative;
- `(asset_id, trade_date, source)` MUST be unique in normalized storage;
- normalized series MUST be ascending by trade date before entering analytical functions;
- duplicate dates MUST raise a data-quality error rather than being silently discarded.

`adjusted_close` is the canonical MVP analytical return price. `close` is the canonical displayed current-price field unless a screen explicitly states otherwise.

## 8.4 Market-bar query and result

**Status: NORMATIVE**

The user-facing market-bar query contains:

```json
{
  "symbols": ["AAPL", "MSFT", "VTI"],
  "start": "2025-01-01",
  "end": "2026-01-01",
  "interval": "1d",
  "provider": "yfinance"
}
```

Rules:

- `symbols` MUST contain between 1 and `MAX_BAR_QUERY_SYMBOLS` entries;
- surrounding whitespace is removed, symbols are canonicalized to uppercase where appropriate, and duplicates are removed while preserving first occurrence;
- a normalized symbol MUST NOT be silently rewritten into a different security;
- `start` is inclusive and `end` is exclusive at the application contract;
- MVP supports `interval = 1d`; additional intervals require an amendment defining time-zone, session, and aggregation rules;
- `provider` is optional and defaults to the configured provider; supplied values MUST belong to a server-side allowlist;
- the request MUST be bounded by the configured maximum history window and maximum output rows.

The response SHALL retain bars by symbol and provide batch-level provenance plus per-symbol status so one invalid or unavailable symbol does not erase successful results for the others:

```json
{
  "results": [
    {
      "symbol": "AAPL",
      "asset_id": "uuid",
      "status": "SUCCEEDED",
      "bars": [
        {
          "trade_date": "2025-01-02",
          "open": 220.10,
          "high": 223.25,
          "low": 219.82,
          "close": 222.40,
          "adjusted_close": 221.97,
          "volume": 48756100
        }
      ],
      "warnings": []
    }
  ],
  "meta": {
    "provider": "yfinance",
    "retrieved_at": "ISO-8601 UTC timestamp",
    "interval": "1d",
    "start": "2025-01-01",
    "end": "2026-01-01"
  }
}
```

Allowed per-symbol states are `SUCCEEDED`, `NOT_FOUND`, `NO_DATA`, and `FAILED`. A structurally valid request completed by the provider returns HTTP 200 and represents all symbol-specific outcomes in `results`, including an all-`NOT_FOUND`/`NO_DATA` batch. A request that fails validation returns HTTP 400; a valid request that cannot be attempted or completed because the configured provider is unavailable returns HTTP 503.

## 8.5 User portfolio

**Status: NORMATIVE**

A portfolio contains at minimum:

```text
id
user_id
name
base_currency       USD
benchmark_asset_id
created_at
updated_at
```

## 8.6 Transaction ledger

**Status: NORMATIVE**

The authoritative source for owned-portfolio holdings is the transaction ledger. Holdings MUST be derived from transactions; a mutable holdings table MUST NOT become the source of truth.

Supported transaction types:

```text
DEPOSIT
WITHDRAWAL
BUY
SELL
DIVIDEND
```

Each transaction MUST have a stable ordering field (`occurred_at` plus an import/source sequence when necessary).

### DEPOSIT / WITHDRAWAL

Required:

```text
cash_amount > 0
```

Asset, quantity, and execution price MUST be absent.

### BUY / SELL

Required:

```text
asset_id
quantity > 0
price > 0
fees >= 0
```

`cash_amount` is derived from quantity, price, fees, and transaction type.

### DIVIDEND

Required:

```text
asset_id
cash_amount > 0
```

Quantity and execution price are optional source metadata, not required accounting inputs.

## 8.7 Monetary precision

**Status: NORMATIVE**

Persisted quantities, prices, fees, and cash values SHALL use fixed-precision decimal database types. Application-ledger arithmetic SHALL use `Decimal`.

Analytical return/risk calculations MAY convert normalized numeric data to `float64` at the explicit boundary between ledger/application logic and the quantitative engine.

## 8.8 Analytical result envelope

**Status: NORMATIVE**

Every substantial analytical response MUST be capable of carrying this metadata:

```json
{
  "result": {},
  "meta": {
    "engine_version": "...",
    "as_of_date": "YYYY-MM-DD",
    "period_start": "YYYY-MM-DD",
    "period_end": "YYYY-MM-DD",
    "data_source": "...",
    "price_field": "adjusted_close",
    "annualization_factor": 252,
    "benchmark": "...",
    "assumptions": {},
    "warnings": []
  }
}
```

A single lightweight endpoint MAY omit fields that are inapplicable, but MUST NOT silently hide a material assumption.

---

# 9. Market Data Rules

## 9.1 Provider abstraction

**Status: NORMATIVE**

Market-data access MUST be provider-agnostic at the application-service boundary.

Conceptually:

```python
from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping, Protocol, Sequence
from uuid import UUID


@dataclass(frozen=True)
class ResolvedProviderAsset:
    asset_id: UUID
    canonical_symbol: str
    provider_symbol: str


@dataclass(frozen=True)
class ProviderIssue:
    code: str
    message: str


@dataclass(frozen=True)
class ProviderBatchResult:
    frames: Mapping[UUID, PriceFrame]
    issues: Mapping[UUID, ProviderIssue]
    retrieved_at: datetime


class MarketDataProvider(Protocol):
    @property
    def name(self) -> str: ...

    def get_daily_bars(
        self,
        assets: Sequence[ResolvedProviderAsset],
        start: date,
        end: date,
    ) -> ProviderBatchResult: ...
```

Required implementations by the end of the MVP:

- yfinance adapter;
- optional Alpaca adapter activated when credentials are configured;
- CSV/sample-data adapter;
- deterministic mock/test adapter.

Provider-specific schemas MUST be normalized before data enters `portfolio_engine`.

Application services depend only on `MarketDataProvider`. Adapter selection SHALL be handled by a provider registry/factory driven by Django settings. Adding a provider MUST require a new adapter and registration, not conditional branches throughout views, services, or the quantitative engine.

## 9.2 Symbol-list request flow

**Status: NORMATIVE**

A multi-symbol request SHALL follow this sequence:

1. a DRF serializer validates the date range, interval, provider name, request bounds, and raw list shape;
2. the application service trims, canonicalizes, and de-duplicates symbols while preserving user order;
3. the asset-resolution service maps canonical symbols to `Asset` and `AssetProviderSymbol` records, creating or refreshing metadata only through an explicit service policy;
4. the provider registry returns the configured/allowed adapter;
5. the adapter retrieves symbols in a batch when the provider supports batching;
6. provider output is normalized into `PriceBar`/`PriceFrame`, validated, and associated with internal asset IDs;
7. successful and unsuccessful symbol results are assembled in the canonical response order;
8. only normalized, validated frames may be cached, persisted, or passed to `portfolio_engine`.

No network call SHALL occur in a model method, serializer, migration, React component, or quantitative-engine function.

## 9.3 yfinance adapter

**Status: NORMATIVE**

yfinance is the default development and public-MVP adapter because it supports credential-free historical data retrieval. It is an infrastructure dependency, not part of the domain contract.

The adapter MUST:

- execute only on the backend;
- request all valid symbols in one provider call when practical;
- set provider options explicitly rather than rely on changing library defaults;
- retrieve unadjusted OHLC plus adjusted close where the provider makes both available;
- preserve the Section 8.4 inclusive-start/exclusive-end contract even when provider semantics differ;
- correctly normalize both single-symbol columns and multi-symbol/MultiIndex columns;
- return an empty per-symbol result for missing data instead of fabricating bars;
- translate provider/network exceptions into stable application errors;
- attach provider name and retrieval time to provenance;
- be covered by recorded/static fixtures or mocked client tests; CI MUST NOT depend on live Yahoo endpoints.

The adapter SHALL use `auto_adjust=False` (or the version-equivalent explicit option) while the canonical contract requires both raw OHLC/close and `adjusted_close`. A future change to adjustment semantics is an analytical behavior change and requires an amendment plus regression fixtures.

Because yfinance is an unofficial convenience adapter intended for research workflows, its terms, availability, throttling behavior, and data semantics MUST be reviewed before any production or commercial launch. Provider failure or throttling MUST be visible; the system MUST NOT silently switch to a different provider because that would change provenance and potentially values.

## 9.4 Alpaca and future adapters

**Status: NORMATIVE**

Alpaca support SHALL implement the same `MarketDataProvider` contract. Credentials remain server-side in environment-backed Django settings. Provider-specific pagination, feed selection, entitlement errors, symbol formats, and rate limits belong inside the adapter.

Future providers MAY be added when they:

- map their identifiers through `AssetProviderSymbol`;
- normalize into the canonical `PriceBar` contract;
- pass the shared provider contract test suite;
- disclose provider/feed provenance;
- define rate-limit, retry, timeout, and partial-failure behavior;
- do not require changes to `portfolio_engine` or frontend chart contracts.

## 9.5 Provider selection, fallback, and caching

**Status: NORMATIVE**

- `MARKET_DATA_DEFAULT_PROVIDER` selects the default adapter; initial development default is `yfinance`.
- `MARKET_DATA_ALLOWED_PROVIDERS` is a server-side allowlist. The client cannot instantiate arbitrary adapters.
- Automatic cross-provider fallback is prohibited for analytical requests. A retry against the same provider MAY occur under the configured retry policy.
- Cache keys MUST include provider, provider symbol, interval, date range, price-adjustment semantics, and normalization version.
- Cached and persisted bars MUST retain their source. Data from different providers MUST NOT be merged into one series without an explicit, disclosed stitching policy.
- Request-level timeouts, bounded retries with jitter, and provider-specific rate limits SHALL be configured centrally.

## 9.6 Price convention

**Status: NORMATIVE**

For MVP historical analytical calculations:

- performance returns use `adjusted_close`;
- benchmark returns use `adjusted_close`;
- covariance/correlation use returns derived from `adjusted_close`;
- optimizer inputs use returns derived from `adjusted_close`;
- MVP backtests use `adjusted_close` as the strategy observation and execution-price basis under the explicit timing model in Section 14;
- current displayed market value uses the latest available raw `close` unless explicitly labeled otherwise.

A single calculation MUST NOT mix raw close returns and adjusted-close returns.

The MVP therefore approximates total-return history through provider-adjusted price series rather than a complete corporate-action cash ledger.

## 9.7 Missing data

**Status: NORMATIVE**

Missing data MUST NOT be silently converted to zero return.

Rules:

- correlation/covariance and optimization SHALL use explicitly aligned observations;
- by default, pairwise statistics use the intersection of valid dates for the relevant series;
- multi-asset optimization uses complete-case dates across the included asset set unless an alternative method is later documented;
- strategy signals MUST NOT forward-fill missing market bars;
- current portfolio valuation MAY use the most recent prior price for up to three trading sessions, but the resulting asset and portfolio MUST be flagged as using stale pricing;
- prices older than the stale-price threshold MUST produce an incomplete-valuation warning or error, not silent carry-forward.

## 9.8 Data quality

**Status: NORMATIVE**

Normalized market data SHALL be validated for:

- duplicate dates;
- non-positive prices;
- impossible OHLC relationships;
- unsorted dates;
- invalid volumes;
- excessive missingness;
- requested-period coverage.

Data quality failures MUST be distinguishable from ordinary insufficient-history conditions.

Validation is applied independently per symbol after normalization. A provider response MUST NOT be treated as complete merely because the outer batch call succeeded. Unexpectedly missing requested symbols, truncated coverage, and duplicate rows SHALL generate explicit per-symbol diagnostics.

---

# 10. Portfolio Accounting Rules

## 10.1 Holdings derivation

**Status: NORMATIVE**

For an owned portfolio, holdings as of time `T` are derived by replaying ledger transactions through `T` in deterministic transaction order.

For each asset:

```text
position_quantity = Σ(BUY quantity) - Σ(SELL quantity)
```

Cash balance is derived from external cash flows and security transactions:

```text
DEPOSIT     increases cash
WITHDRAWAL  decreases cash
BUY         decreases cash by quantity × price + fees
SELL        increases cash by quantity × price - fees
DIVIDEND    increases cash
```

The MVP is long-only. A transaction that would create a negative security position MUST be rejected unless the portfolio is explicitly operating in an incomplete-import mode. Incomplete-import mode, if implemented, MUST be clearly labeled and MUST NOT silently pretend the ledger is complete.

## 10.2 Portfolio market value

**Status: NORMATIVE**

At valuation date `t`:

```text
security_value_i,t = quantity_i,t × market_price_i,t
portfolio_value_t  = cash_t + Σ security_value_i,t
```

Current allocation weight:

```text
weight_i,t = security_value_i,t / portfolio_value_t
cash_weight_t = cash_t / portfolio_value_t
```

Weights are undefined if total portfolio value is less than or equal to zero.

## 10.3 External versus internal cash flows

**Status: NORMATIVE**

For performance purposes:

- DEPOSIT and WITHDRAWAL are external cash flows;
- BUY and SELL are internal reallocations and MUST NOT be treated as portfolio contributions or withdrawals;
- DIVIDEND is portfolio investment income and is not an external cash flow.

## 10.4 Daily time-weighted return

**Status: NORMATIVE**

For owned portfolios with external flows, the canonical daily return is:

```text
r_t = (V_t - CF_t) / V_(t-1) - 1
```

where:

- `V_t` is end-of-day portfolio value;
- `V_(t-1)` is prior end-of-day portfolio value;
- `CF_t` is net external flow during day `t`, with deposits positive and withdrawals negative.

This convention treats the external flow adjustment consistently for daily chaining. If future intraday cash-flow precision is required, this formula MUST be revisited by amendment rather than silently changed.

Time-weighted cumulative return is:

```text
TWR = Π(1 + r_t) - 1
```

---

# 11. Mathematical and Analytical Definitions

**Status: NORMATIVE**

This section defines canonical formulas. Alternative definitions MUST NOT be substituted without a guide amendment and updated validation tests.

## 11.1 Simple return

For analytical price `P_t`:

```text
r_t = P_t / P_(t-1) - 1
```

## 11.2 Log return

```text
ℓ_t = ln(P_t / P_(t-1))
```

Log return MAY be exposed for analysis but SHALL NOT replace simple return in portfolio wealth chaining.

## 11.3 Cumulative return

```text
R_cum = Π(1 + r_t) - 1
```

## 11.4 CAGR / annualized geometric return

For ending wealth ratio `G = 1 + R_cum` and `D` elapsed calendar days:

```text
CAGR = G^(365.2425 / D) - 1
```

The function MUST reject a non-positive wealth ratio. The result MUST be labeled as annualized when the analyzed period is shorter than one year.

## 11.5 Annualized volatility

Using daily simple returns and sample standard deviation:

```text
σ_annual = std(r_daily, ddof=1) × √252
```

At least two valid return observations are mathematically required; application-level minimum-history requirements may be stricter.

## 11.6 Risk-free conversion

An annual effective risk-free rate is converted to a daily effective rate as:

```text
rf_daily = (1 + rf_annual)^(1/252) - 1
```

The MVP default is `rf_annual = 0.0`, but callers MAY supply another explicit value.

## 11.7 Sharpe ratio

Using daily returns:

```text
excess_t = r_t - rf_daily
Sharpe = mean(excess_t) / std(excess_t, ddof=1) × √252
```

If the denominator is zero or insufficient valid observations exist, the result MUST be `null`/undefined with an explanatory warning. The engine MUST NOT return positive or negative infinity as a normal API value.

## 11.8 Sortino ratio

Let annual minimum acceptable return be `MAR_annual`, defaulting to zero. Convert it to daily form using the same effective-rate convention as the risk-free rate.

```text
excess_t = r_t - MAR_daily
negative_t = min(excess_t, 0)
downside_deviation = sqrt(mean(negative_t²))
Sortino = mean(excess_t) / downside_deviation × √252
```

If downside deviation is zero, the result MUST be undefined with a warning rather than infinity.

## 11.9 Wealth index and drawdown

Starting from normalized wealth `W_0 = 1`:

```text
W_t = Π_(j≤t)(1 + r_j)
Peak_t = max(W_0 ... W_t)
Drawdown_t = W_t / Peak_t - 1
MaxDrawdown = min(Drawdown_t)
```

Maximum drawdown is therefore zero or negative.

## 11.10 Beta

Using date-aligned daily portfolio returns `r_p` and benchmark returns `r_b`:

```text
Beta = Cov(r_p, r_b) / Var(r_b)
```

Sample covariance/variance conventions SHALL be used consistently. Beta is undefined when benchmark variance is zero or valid history is below the configured minimum observation count.

## 11.11 Correlation

Pearson correlation is the canonical MVP correlation measure. Pairwise correlations use date intersections after dropping invalid observations.

Correlation results MUST include or make available the observation count used for each pair when exposed diagnostically.

## 11.12 Hypothetical weighted portfolio return

For a hypothetical portfolio rebalanced to weights known before period `t`:

```text
r_portfolio,t = Σ_i w_(i,t-1) × r_(i,t)
```

Using same-period ending weights to calculate that period's return is prohibited because it introduces hindsight.

## 11.13 Concentration

The MVP SHALL calculate at least:

### Largest-position weight

```text
max_i(w_i)
```

### Herfindahl-Hirschman-style concentration index

```text
HHI = Σ_i w_i²
```

Cash MAY be reported separately and MUST be clearly identified as included or excluded from an HHI result. The default portfolio-security HHI excludes cash unless the result name explicitly states otherwise.

## 11.14 Rolling returns

A rolling `N`-period simple cumulative return ending at `t` is:

```text
R_(t,N) = Π_(j=t-N+1..t)(1 + r_j) - 1
```

Rolling windows MUST contain only observations available through their ending date.

---

# 12. Portfolio Optimization

## 12.1 MVP assumptions

**Status: NORMATIVE**

MVP optimizations are:

- long-only;
- unlevered;
- fully invested across the included risky assets unless cash is explicitly modeled as an optimization asset in a future amendment;
- based on historical daily adjusted-close returns;
- deterministic for identical inputs.

## 12.2 Expected returns

**Status: NORMATIVE**

Default annual expected return vector:

```text
μ_i = mean(daily simple returns_i) × 252
```

This is a historical estimator, not a forecast claim. The UI MUST describe optimized portfolios as historical/model-based results rather than predictions.

## 12.3 Covariance matrix

**Status: NORMATIVE**

Default annual covariance matrix:

```text
Σ_annual = Cov(daily returns, ddof=1) × 252
```

The matrix MUST be computed from the complete-case aligned return dataset for the optimization asset set in MVP.

## 12.4 Weight constraints

**Status: NORMATIVE**

Canonical constraints:

```text
Σ_i w_i = 1
min_weight_i ≤ w_i ≤ max_weight_i
```

Default MVP bounds are:

```text
0 ≤ w_i ≤ 1
```

User-specified maximum weights MAY make the optimization infeasible. Infeasibility MUST be surfaced as an optimization failure, not silently weakened.

## 12.5 Minimum-variance portfolio

**Status: NORMATIVE**

Objective:

```text
minimize  wᵀΣw
```

subject to Section 12.4 constraints.

## 12.6 Maximum-Sharpe portfolio

**Status: NORMATIVE**

Objective:

```text
maximize  (μᵀw - rf_annual) / sqrt(wᵀΣw)
```

subject to Section 12.4 constraints.

## 12.7 Equal-weight portfolio

**Status: NORMATIVE**

For `N > 0` included assets:

```text
w_i = 1 / N
```

## 12.8 Efficient frontier

**Status: NORMATIVE**

The efficient frontier SHALL be generated through repeated constrained variance minimization at explicit target-return levels across the feasible return range.

Each frontier point MUST satisfy the same portfolio constraints as the compared optimized portfolios.

Failed points MUST NOT be plotted as valid frontier results.

## 12.9 Solver behavior

**Status: NORMATIVE**

SciPy optimization is the canonical initial implementation.

After solving:

- solver success MUST be checked;
- all constraints MUST be independently revalidated;
- weight sum MUST be within the optimization tolerance;
- bounds MUST be within tolerance;
- non-finite values MUST fail validation;
- tiny numerical residual weights MAY be zeroed only when the result remains within tolerance after normalization.

The engine MUST NOT accept a solver result merely because the library returned an array.

## 12.10 External validation

**Status: NORMATIVE**

At least selected optimization fixtures MUST be independently compared against a recognized external implementation or analytically solvable cases in the validation test suite.

External libraries MAY be test/development dependencies for validation, but MUST NOT replace the project's own core optimizer implementation in the runtime path of the MVP.

---

# 13. Rebalancing

## 13.1 Target allocations

**Status: NORMATIVE**

Target weights MUST satisfy:

```text
Σ target_weight = 1
0 ≤ target_weight ≤ 1
```

within the configured tolerance.

Targets MAY include a cash target.

## 13.2 Drift

**Status: NORMATIVE**

For asset `i`:

```text
absolute_drift_i = current_weight_i - target_weight_i
relative_drift_i = absolute_drift_i / target_weight_i
```

Relative drift is undefined when `target_weight_i = 0`; the API MUST represent that case explicitly rather than divide by zero.

## 13.3 Simulated rebalance trade

**Status: NORMATIVE**

Given current total investable portfolio value `V`:

```text
target_value_i = V × target_weight_i
trade_notional_i = target_value_i - current_value_i
```

Interpretation:

- positive trade notional = simulated buy;
- negative trade notional = simulated sell.

MVP rebalance output is a simulation. It MUST NOT be labeled as an order or executed trade.

## 13.4 Scheduled rebalancing

**Status: NORMATIVE**

Supported initial schedules:

- monthly;
- quarterly;
- annual.

A scheduled rebalance decision is made using weights observable at the scheduled decision date and executed under the backtest timing model in Section 14.

## 13.5 Threshold rebalancing

**Status: NORMATIVE**

A threshold rebalance is triggered when at least one included asset satisfies:

```text
abs(current_weight_i - target_weight_i) >= drift_threshold
```

The decision MUST use only information available at the decision timestamp.

---

# 14. Backtesting and Anti-Look-Ahead Rules

## 14.1 Purpose

**Status: NORMATIVE**

The backtesting engine exists to simulate deterministic historical strategy behavior under explicit assumptions. It does not prove future profitability.

Preventing look-ahead bias is a first-class architectural requirement, not only a testing concern.

## 14.2 MVP frequency

**Status: NORMATIVE**

MVP backtests operate on daily bars only.

Intraday strategies are excluded.

## 14.3 Observe-now, execute-later rule

**Status: NORMATIVE**

At the end of trading date `t`:

1. the strategy MAY observe data whose timestamp/date is `<= t`;
2. the strategy generates a signal or target based only on that data;
3. the resulting trade is eligible to execute at the canonical execution price on the next available trading date `t+1`.

The MVP canonical execution price is the next trading day's `adjusted_close`.

Therefore:

```text
observe through close(t)
      ↓
generate signal(t)
      ↓
execute at adjusted_close(t+1)
```

This one-bar delay is intentional. A strategy MUST NOT consume the final close of day `t` and then pretend it executed at that same close.

A future amendment MAY introduce next-open execution using a consistently adjusted execution-price series.

## 14.4 Structural prevention of future-data access

**Status: NORMATIVE**

The strategy interface MUST NOT receive an unrestricted full-future dataframe and rely only on developer discipline.

The engine SHALL provide a strategy context whose visible history ends at the current decision date.

Conceptually:

```python
@dataclass(frozen=True)
class StrategyContext:
    as_of: date
    history: PriceFrame   # guaranteed max(history.date) <= as_of
    portfolio: PortfolioState
```

Architecture or behavioral tests MUST prove that `history` cannot contain later timestamps for normal strategy execution.

## 14.5 Orders and fills

**Status: NORMATIVE**

The MVP may express strategy output as either target weights or normalized order intents. The execution layer, not the strategy, owns conversion into simulated fills.

Execution assumptions MUST be explicit.

For a buy at reference price `P` with slippage rate `s`:

```text
fill_price = P × (1 + s)
```

For a sell:

```text
fill_price = P × (1 - s)
```

Commission/fee:

```text
fee = abs(fill_notional) × commission_rate
```

Defaults MAY be zero, but a backtest result MUST retain the assumptions used.

## 14.6 Cash and position constraints

**Status: NORMATIVE**

MVP backtests:

- do not allow short positions;
- do not allow margin borrowing;
- do not intentionally create negative cash;
- permit fractional shares to keep portfolio-allocation analysis separate from lot-size effects.

If an intended order cannot be fully funded, the execution layer MUST follow one documented deterministic policy. The initial policy is to scale the buy quantity down to the maximum affordable non-negative-cash amount after estimated costs.

## 14.7 Strategy warm-up

**Status: NORMATIVE**

Strategies requiring historical windows MUST declare a minimum warm-up observation count.

No trade signal may be generated before sufficient historical observations exist.

Example:

```text
200-day moving average → at least 200 valid prior/current observations
```

## 14.8 Moving-average strategy

**Status: NORMATIVE**

Initial long-only moving-average strategy:

```text
long signal when fast_MA_t > slow_MA_t
cash signal otherwise
```

The moving averages are calculated only from history available through `t`; resulting position changes execute at `t+1` under Section 14.3.

## 14.9 Momentum strategy

**Status: NORMATIVE**

The initial momentum strategy SHALL define momentum from historical price performance over an explicit lookback window ending at `t`, with any skip-period choice documented in the strategy parameters.

The first MVP implementation MUST choose one canonical definition and test it. Additional momentum definitions are separate strategy variants, not silent changes to the same named strategy.

## 14.10 Benchmark comparisons

**Status: NORMATIVE**

The UI SHALL distinguish:

1. a frictionless benchmark total-return series used as a market reference; and
2. a buy-and-hold strategy simulated through the same backtest engine when transaction-cost comparability is desired.

These are not interchangeable and MUST be labeled accordingly.

## 14.11 Known historical-backtest limitations

**Status: NORMATIVE**

MVP documentation and backtest result warnings MUST disclose relevant limitations, including:

- historical results do not predict future results;
- user-selected/static asset universes do not remove survivorship bias;
- adjusted-price backtests approximate corporate-action economics rather than modeling all actions explicitly;
- daily-bar execution cannot model intraday path or liquidity;
- slippage and commission assumptions are simplified;
- delisted-security handling is not complete in MVP.

## 14.12 Prohibited backtest behavior

**Status: NORMATIVE**

The following are defects:

- using `t+1` data to generate a `t` signal;
- calculating a signal from day `t` close and filling at day `t` close;
- using ending-period weights to calculate same-period hypothetical return;
- silently filling missing signal data with future values;
- optimizing strategy parameters on the full test period and presenting the same period as unbiased out-of-sample performance without disclosure;
- discarding losing trades or failed executions from summary statistics;
- using a benchmark with a different time interval without explicit date alignment.

---

# 15. Application API Contract

## 15.1 Versioning

**Status: NORMATIVE**

All public API routes SHALL be versioned beneath:

```text
/api/v1
```

## 15.2 Resource groups

**Status: NORMATIVE**

The intended resource surface is:

```text
/assets
/market-data/providers
/market-data/bars/query
/portfolios
/portfolios/{id}/transactions
/portfolios/{id}/holdings
/analytics
/optimization-runs
/rebalance-simulations
/backtest-runs
```

Exact endpoint paths MAY evolve within Phase 1 before public release, but the application SHALL preserve resource-oriented semantics.

## 15.3 API schemas

**Status: NORMATIVE**

- ORM models MUST NOT be returned directly.
- Request and response schemas MUST use explicit Django REST Framework serializers. `ModelSerializer` MAY be used for straightforward CRUD resources, but analytical, provider, and run contracts SHOULD use plain `Serializer` classes so the public contract is not accidentally coupled to ORM fields.
- Decimal money values MUST be serialized using a documented precision-safe convention.
- Dates and timestamps MUST use ISO 8601 representations.
- Analytical missing/undefined values MUST serialize as `null` plus warnings/diagnostics; `NaN` and infinity MUST NOT appear in JSON responses.
- The OpenAPI schema generated by `drf-spectacular` is the authoritative frontend integration contract and MUST be checked for unintended changes in CI.

## 15.4 Market-bar query API

**Status: NORMATIVE**

The initial endpoint is:

```text
POST /api/v1/market-data/bars/query
```

POST is intentional because a bounded list of symbols plus date-range and provider options is a query document that can exceed practical URL limits. The endpoint is read-only and idempotent; it MUST NOT mutate a user's portfolio.

The endpoint SHALL:

- accept the Section 8.4 request contract;
- apply DRF throttling in addition to provider-specific rate limiting;
- authorize use of any non-default provider;
- preserve canonical symbol order in the response;
- expose partial per-symbol failures without discarding successful bars;
- include cache/provenance metadata without exposing credentials or upstream secrets.

`GET /api/v1/market-data/providers` MAY expose safe provider capabilities such as name, availability, supported intervals, and maximum history. It MUST NOT expose credentials or secret configuration.

## 15.5 Error schema

**Status: NORMATIVE**

Application errors SHOULD conform to a stable shape:

```json
{
  "error": {
    "code": "INSUFFICIENT_DATA",
    "message": "...",
    "details": {},
    "trace_id": "..."
  }
}
```

Stable error codes MUST distinguish at least:

- validation error;
- authorization/not-found boundary;
- insufficient analytical history;
- market-data quality failure;
- stale/incomplete valuation;
- optimization infeasibility;
- optimization solver failure;
- invalid portfolio weights;
- backtest configuration error;
- asynchronous run failure.

Market-data APIs additionally distinguish:

- unsupported provider;
- provider unavailable or throttled;
- unresolved symbol;
- no data for the requested period;
- request limit exceeded.

## 15.6 Run resources

**Status: NORMATIVE**

Optimization and backtesting SHALL use persisted run resources even if the first implementation executes some runs synchronously.

Canonical run states:

```text
PENDING
RUNNING
SUCCEEDED
FAILED
```

This preserves a stable API when heavy calculations later move to workers.

---

# 16. Frontend Contract

## 16.1 Role of frontend

**Status: NORMATIVE**

The frontend is responsible for:

- navigation;
- input collection;
- validation feedback;
- charting;
- comparison workflows;
- explanatory copy;
- assumptions/warnings visibility;
- accessible formatting.

The frontend is not authoritative for financial calculations.

Apache ECharts is the normative visualization library. Chart components MUST consume canonical API results or presentation-only transforms of those results. They MUST NOT compute authoritative portfolio, risk, optimization, or backtest metrics.

## 16.2 Primary MVP screens

**Status: NORMATIVE**

The public MVP SHALL provide:

1. Market Data Explorer
2. Portfolio Dashboard
3. Portfolio Analysis
4. Allocation Lab
5. Rebalancing Lab
6. Backtesting / Strategy Lab
7. Portfolio/transaction management

The Market Data Explorer SHALL provide:

- a ticker-list input accepting comma-, whitespace-, or newline-separated symbols;
- visible normalized symbol chips before submission;
- start and end date inputs;
- a provider selector populated from the safe provider-capabilities endpoint when more than one provider is enabled;
- loading, empty, partial-success, rate-limit, and failure states;
- one selectable/legend-addressable price series per successful symbol;
- a candlestick-plus-volume view for an individual selected symbol;
- disclosure of provider, retrieval time, date coverage, adjustment convention, and warnings.

## 16.3 Required analytical context

**Status: NORMATIVE**

A metric card or chart MUST show enough context to avoid misleading interpretation. Depending on the metric, this includes:

- period;
- benchmark;
- annualized vs cumulative labeling;
- warning state;
- stale-data state;
- cost assumptions for backtests;
- simulation/not-advice language where relevant.

## 16.4 No false precision

**Status: NORMATIVE**

The UI SHOULD avoid displaying more precision than is meaningful. Suggested defaults:

- currency: 2 decimals;
- allocation weights: 1 decimal percentage point;
- returns/volatility: 1–2 decimal percentage points;
- ratios: 2 decimals;
- correlations/beta: 2 decimals.

Raw values remain available to the application; display rounding MUST NOT modify stored or downstream calculation values.

## 16.5 ECharts implementation rules

**Status: NORMATIVE**

- The frontend SHALL depend on the `echarts` package; any React wrapper is optional and MUST be documented if adopted.
- A shared chart component/hook SHALL own ECharts initialization, responsive resizing, theme application, option updates, event cleanup, and `dispose()` on unmount.
- ECharts option construction SHALL live in typed presentation modules, not page components.
- Price-line datasets use ISO trade dates and raw numeric values from the API.
- Candlestick data MUST map each bar to ECharts order `[open, close, low, high]`; this ordering SHALL have a dedicated unit test.
- Volume MUST be rendered on a separate aligned grid/axis from price and retain the same ordered category dates.
- Missing observations MUST remain gaps unless a specific chart is explicitly labeled as interpolated. Visual interpolation MUST never be sent back into analytics.
- Multi-symbol comparisons SHOULD default to normalized growth (`100` at the common visible start) only when clearly labeled; raw-price comparison MUST remain available. If normalized growth is calculated client-side for display, it is presentation-only and MUST be tested and labeled.
- Tooltips, legends, axis units, keyboard-accessible surrounding summaries, and non-color-only warning cues are required.
- Large datasets SHOULD use ECharts dataset/typed-array-friendly shapes, progressive rendering, and data zoom rather than rendering an unbounded number of DOM elements.
- All chart instances SHALL use the shared theme tokens derived from Tailwind design tokens; hard-coded one-off palettes are prohibited.

## 16.6 Market-data frontend state

**Status: NORMATIVE**

TanStack Query owns remote bar-query state. The query key MUST include normalized symbols in display order, start, end, interval, and provider. User input text remains local form state until submitted; it MUST NOT trigger a provider request on every keystroke.

The frontend MAY reshape bars into ECharts datasets, but MUST preserve the canonical API response in query state. Per-symbol failures and warnings SHALL remain visible even when other symbols chart successfully.

---

# 17. Asynchronous Work and Reproducibility

## 17.1 Determinism

**Status: NORMATIVE**

Given identical normalized input data, configuration, engine version, and deterministic strategy parameters, an analytical or backtest run MUST produce equivalent outputs within documented numerical tolerance.

Randomized methods are not part of MVP. Any future randomized calculation MUST require an explicit stored random seed for reproducibility.

## 17.2 Run provenance

**Status: NORMATIVE**

Persisted optimization/backtest runs SHALL store or reference enough information to reproduce the run, including:

- run ID;
- engine version;
- strategy/optimization method and version;
- serialized parameters;
- date range;
- included assets;
- benchmark;
- transaction-cost/slippage assumptions;
- risk-free-rate assumption when applicable;
- source-data version, retrieval identity, or deterministic data hash where practical;
- status;
- start/completion timestamps;
- failure code/message if failed.

## 17.3 Background jobs

**Status: NORMATIVE**

Lightweight analytical summaries MAY execute in-process.

Computationally heavier backtests, parameter sweeps, or optimization batches SHOULD execute through the worker boundary once their runtime justifies it.

Moving execution to Celery MUST NOT change the analytical result contract.

---

# 18. AI Insight Layer

**Status: NORMATIVE FOR POST-MVP DESIGN**

The AI layer begins only after deterministic analytics and backtesting meet their release gates.

## 18.1 Grounding rule

A language model MUST NOT be the authoritative calculator for:

- return;
- volatility;
- drawdown;
- Sharpe/Sortino;
- beta;
- correlation;
- optimization weights;
- rebalance quantities;
- backtest statistics.

The model receives structured analytical results and produces explanations of those results.

## 18.2 Tool-mediated analytics

The intended future flow is:

```text
User question
    ↓
Intent / tool selection
    ↓
Deterministic analytics function
    ↓
Structured result + provenance
    ↓
LLM explanation
```

If the deterministic engine cannot answer the requested question, the AI MUST state the limitation rather than fabricate a calculation.

## 18.3 Recommendation boundary

The AI SHOULD use language such as:

- "historically..."
- "under these assumptions..."
- "this simulation shows..."
- "the largest measured contributor was..."

It SHOULD NOT present personalized investment directives as authoritative advice.

---

# 19. Testing Strategy

## 19.1 Testing philosophy

**Status: NORMATIVE**

The project SHALL use a testing diamond:

- dense unit and property tests around the quantitative engine and services;
- focused integration tests around persistence/provider/API boundaries;
- thinner end-to-end UI tests for critical workflows.

Tests MUST prove behavior, not only code execution.

A green test suite is not sufficient if the tests merely reproduce the same incorrect formula as the implementation.

## 19.2 Test categories

**Status: NORMATIVE**

Required categories:

```text
unit/
property/
integration/
validation/
architecture/
```

Frontend additionally uses component tests and Playwright end-to-end tests.

## 19.3 Mathematical unit tests

**Status: NORMATIVE**

At minimum, tests SHALL include analytically obvious fixtures:

### Returns

- constant price -> zero return;
- price doubles -> 100% simple cumulative return;
- known multi-period compounding fixture.

### Volatility

- constant returns -> zero volatility;
- known small return vector -> independently verified sample standard deviation.

### Drawdown

- monotonic increasing wealth -> maximum drawdown = 0;
- known peak/trough fixture -> exact expected drawdown.

### Portfolio

- equal weighted identical assets -> same return as either asset;
- weights sum to one;
- portfolio value equals cash plus security market value.

## 19.4 Property-based invariants

**Status: NORMATIVE**

Hypothesis SHOULD test invariants including:

- cumulative wealth from valid returns never depends on future elements;
- normalized allocation weights sum to one when portfolio value is positive;
- HHI lies within valid long-only bounds;
- increasing transaction costs cannot improve the net return of an otherwise identical deterministic backtest;
- a zero-trade backtest produces zero transaction fees;
- a sell cannot increase position quantity;
- a buy cannot reduce position quantity;
- drawdown is never positive under the canonical definition.

## 19.5 Optimizer tests

**Status: NORMATIVE**

Tests SHALL prove:

- sum of weights is within tolerance of one;
- weights obey configured bounds;
- minimum-variance result is not more volatile than a feasible equal-weight solution within tolerance;
- known two-asset fixtures produce independently validated results;
- infeasible constraints fail explicitly;
- solver failure cannot be serialized as a successful optimization.

## 19.6 Anti-look-ahead tests

**Status: NORMATIVE**

The backtest suite MUST include explicit tripwire tests proving:

1. strategy context never contains a date greater than `as_of`;
2. a close-based signal generated on `t` cannot fill on `t`;
3. modifying future prices after decision date `t` cannot change the signal computed at `t`;
4. warm-up windows do not consume observations after the decision date;
5. rolling indicators use backward-looking windows only;
6. rebalancing decisions do not use post-decision prices;
7. parameter selection and reported evaluation periods are labeled when the same sample is used for both.

These are release-blocking tests.

## 19.7 External validation tests

**Status: NORMATIVE**

Selected canonical calculations SHALL be compared with independent sources or implementations.

Examples:

- NumPy/pandas independently constructed formulas;
- analytically solvable fixtures;
- optional development-only comparison with established portfolio/backtesting libraries.

Validation tests SHOULD avoid sharing the exact production helper under test, or they risk false agreement.

## 19.8 Ledger integration tests

**Status: NORMATIVE**

Required scenarios include:

- deposit -> buy -> value;
- buy -> partial sell;
- sell exceeding position rejected;
- fees change cash correctly;
- dividend increases cash but not security quantity;
- external cash flow does not create investment return in TWR;
- buy/sell does not count as an external portfolio contribution/withdrawal.

## 19.9 API tests

**Status: NORMATIVE**

API tests SHALL prove:

- DRF serializer validation and stable error mapping;
- portfolio ownership boundary;
- missing-data error mapping;
- undefined analytical metric serialization as null plus warning;
- NaN/infinity never appear in JSON;
- run-state transitions;
- failed optimization/backtest runs remain auditable;
- OpenAPI generation succeeds and contains the public routes.

## 19.10 Frontend end-to-end tests

**Status: NORMATIVE**

At minimum, Playwright SHALL cover:

1. enter at least three ticker symbols and retrieve bars;
2. view a multi-symbol comparison and an individual candlestick/volume chart;
3. see a per-symbol warning while valid symbols remain charted;
4. load sample portfolio;
5. view performance/risk summary;
6. change analysis period;
7. create target allocation and simulate rebalance;
8. run one backtest and view results;
9. see warnings when data/metrics are insufficient.

## 19.11 Market-data provider and chart tests

**Status: NORMATIVE**

Every `MarketDataProvider` implementation SHALL pass the same contract suite using deterministic fixtures. The suite proves:

- multiple requested symbols remain associated with the correct internal asset IDs;
- returned bars are ascending, unique by date, and valid under Section 8.3;
- the requested inclusive-start/exclusive-end interval is honored;
- single-symbol and multi-symbol provider response shapes normalize identically;
- empty, missing, throttled, and partially failed responses map to stable statuses/errors;
- source and retrieval provenance are present;
- provider secrets never appear in serialized responses or logs.

yfinance and Alpaca integration tests MUST mock or record the provider client boundary. Live-provider smoke tests MAY run manually or in a non-blocking scheduled workflow, but MUST NOT be required for deterministic pull-request CI.

Frontend unit/component tests SHALL prove:

- ticker parsing handles comma, whitespace, newline, duplicates, and empty tokens;
- the TanStack Query key changes for any material request input;
- candlestick tuples use `[open, close, low, high]`;
- price and volume datasets share ordered dates;
- chart lifecycle cleanup disposes the ECharts instance;
- per-symbol failures remain visible during partial success.

---

# 20. Observability, Provenance, and Auditability

## 20.1 Logging

**Status: NORMATIVE**

Application logs SHALL be structured and SHOULD include:

- trace/request ID;
- run ID when applicable;
- user/portfolio identifiers in non-secret internal form where appropriate;
- operation;
- duration;
- success/failure code.

Sensitive tokens, credentials, and full private payloads MUST NOT be logged.

## 20.2 Analytical provenance

**Status: NORMATIVE**

A reviewer SHALL be able to determine, for a persisted optimization/backtest result:

- what data interval was used;
- what assets were included;
- what strategy/method and parameters were used;
- what execution-cost assumptions were used;
- what engine version generated it;
- whether the run succeeded or failed;
- what warnings were active.

## 20.3 Warning policy

**Status: NORMATIVE**

Warnings MUST be explicit structured data, not only prose buried in logs.

Examples:

```text
INSUFFICIENT_HISTORY
STALE_PRICE
INCOMPLETE_VALUATION
HIGH_MISSINGNESS
UNDEFINED_SHARPE
UNDEFINED_SORTINO
UNDEFINED_BETA
BACKTEST_LIMITATION_SURVIVORSHIP_BIAS
```

---

# 21. Security, Privacy, and Product Positioning

## 21.1 Portfolio ownership

**Status: NORMATIVE**

Every user-owned portfolio query or mutation MUST be scoped by the authenticated user's identity at the application-service/repository boundary.

A client-provided `user_id` MUST NOT be trusted as authorization.

## 21.2 Authentication architecture

**Status: NORMATIVE**

Authentication SHALL use Django/DRF authentication classes behind the framework boundary so local development can use a deterministic development identity while deployed environments can use a standards-based authentication provider without changing portfolio services.

Any development authentication bypass MUST:

- be impossible to enable accidentally in production configuration;
- be clearly labeled;
- be covered by configuration tests.

Production SHOULD serve the React application and API from the same site when practical. If session authentication is used, unsafe methods MUST enforce Django CSRF protection. If a cross-origin deployment is required, allowed origins MUST be explicit and environment-specific; permissive wildcard CORS with credentials is prohibited. Authentication choice MUST be documented before protected portfolio endpoints are exposed.

## 21.3 Secrets

**Status: NORMATIVE**

- secrets MUST come from environment/configuration, not committed source;
- `.env.example` MUST contain placeholders only;
- external market-data API tokens MUST never be sent to the browser;
- frontend code MUST NOT directly call a privileged market-data provider using a secret token.

## 21.4 Product positioning

**Status: NORMATIVE**

The product SHALL identify itself as analytical/research/simulation software and SHALL include visible language that historical results are not guarantees of future performance.

Simulation outputs such as optimized weights and rebalance trades MUST be labeled as model/simulation outputs rather than personalized fiduciary advice.

---

# 22. Performance and Reliability

## 22.1 Performance principles

**Status: NORMATIVE**

Correctness takes precedence over premature optimization.

The engine SHOULD use vectorized NumPy/pandas operations where they improve clarity and performance without weakening correctness.

A performance optimization MUST NOT change a mathematical result outside documented tolerance.

## 22.2 Caching

**Status: NORMATIVE**

Caching MAY be used for:

- normalized historical price bars;
- asset metadata;
- expensive analytical summaries with explicit input/version keys;
- completed immutable run outputs.

Cache keys for analytical results MUST incorporate enough information to avoid serving a result generated from different inputs or engine semantics.

Multi-symbol market-data requests MUST be bounded by symbol count, date span, and estimated/actual row count. The service SHOULD batch provider calls and cache validated normalized bars. A cache hit MUST preserve or reconstruct correct source provenance and MUST NOT be presented as a new upstream retrieval.

## 22.3 Performance budgets

**Status: INFORMATIVE until a benchmark host is established**

Initial engineering targets on a typical developer workstation:

- portfolio summary for 25 assets / 10 years of daily data: approximately < 1 second after data are loaded;
- single-asset 20-year daily strategy backtest: approximately < 1 second;
- 50-asset covariance/optimization run: approximately < 2 seconds.

These are design targets, not CI gates until a reproducible benchmark environment exists.

---

# 23. MVP Acceptance Criteria

## 23.1 Definition of public MVP

**Status: NORMATIVE**

The public MVP is **v0.3.0**. It is not complete merely because a dashboard renders or calculations run in a notebook.

The MVP is accepted only when all categories below pass.

## 23.2 Repository and platform gate

- repository structure conforms to Section 5;
- backend and frontend start from documented local commands;
- Docker Compose starts required development services;
- migrations apply cleanly to an empty database;
- CI runs linting, typing, backend tests, frontend tests, and build checks;
- sample environment configuration contains no secrets.

## 23.3 Data gate

- sample/CSV market-data adapter works without an external account;
- yfinance adapter retrieves and normalizes a bounded multi-symbol daily-bar request in a live smoke test;
- optional Alpaca adapter works when credentials and entitlements are supplied;
- all enabled providers pass the shared deterministic provider contract suite;
- normalized price-bar validation is active;
- data gaps produce documented behavior;
- sample datasets are sufficient to run the README demo offline;
- the API returns partial per-symbol status without losing successful symbols.

## 23.4 Portfolio analytics gate

For a sample portfolio, the application successfully displays and API-exposes:

- current value;
- allocation;
- TWR/cumulative return;
- annualized return;
- volatility;
- Sharpe;
- Sortino;
- maximum drawdown;
- beta;
- correlation;
- rolling return output;
- benchmark comparison.

All canonical metrics have independent tests.

## 23.5 Optimization gate

The user can:

- compare current, equal-weight, minimum-variance, and maximum-Sharpe allocations;
- view an efficient frontier;
- specify allowed weight bounds;
- receive explicit failure for infeasible constraints;
- inspect assumptions and analysis period;
- reproduce a persisted optimization run.

## 23.6 Rebalancing gate

The user can:

- define target weights;
- see current versus target weights;
- see drift;
- generate simulated trade notionals;
- compare at least annual, quarterly, and threshold-based historical rebalancing;
- see turnover/trade counts and performance effects for compared rules.

## 23.7 Backtesting gate

The user can run:

- buy and hold;
- moving-average strategy;
- momentum strategy.

Each run exposes:

- equity curve;
- drawdown curve;
- trade history;
- CAGR/annualized return;
- volatility;
- Sharpe;
- Sortino;
- maximum drawdown;
- benchmark comparison;
- transaction-cost/slippage assumptions;
- run provenance.

All Section 19.6 anti-look-ahead tests pass.

## 23.8 UX gate

- user can complete the main workflows without editing code;
- user can paste a list of ticker symbols and render returned bars without creating a portfolio first;
- warnings are visible and understandable;
- loading and run states are visible;
- failed runs explain why they failed;
- charts have titles, units, legends, and accessible labels;
- ECharts price, volume, allocation, risk, optimization, and backtest views use shared components and theme tokens;
- no screen presents model/simulation output as guaranteed future performance.

## 23.9 Documentation gate

The repository contains at least:

- high-quality README;
- architecture overview;
- this development guide;
- analytics methodology reference;
- API documentation;
- sample-data documentation;
- known backtest limitations;
- setup instructions;
- screenshots or demo material;
- clear project roadmap.

---

# 24. Phased Implementation Order

**Status: NORMATIVE**

Implementation SHALL proceed in this order unless an amendment deliberately changes sequencing.

## Phase 0 — Canonical specification

Deliverables:

- `docs/dev-guide.md`;
- initial architecture decisions;
- mathematical definitions;
- MVP scope;
- release gates.

Exit gate:

- the team agrees this document is the baseline before broad code generation.

## Phase 1 — Repository and platform foundation

Build:

- monorepo structure;
- Django project and domain-app scaffold;
- custom Django user model selected before the first migration;
- frontend package scaffold;
- Django/DRF health endpoint;
- React shell;
- PostgreSQL;
- Django migrations;
- Docker Compose;
- Ruff/mypy/pytest/pytest-django;
- TypeScript/Vitest;
- GitHub Actions;
- environment-specific Django settings and secrets pattern;
- generated OpenAPI contract.

Do NOT build optimization, backtesting, or AI here.

Exit gate:

- clean clone -> documented setup -> frontend/API/database healthy;
- CI green.

## Phase 2 — Canonical market-data and analytical contracts

Build:

- `PriceBar` normalized contract;
- market-data provider protocol;
- provider registry/factory;
- asset and provider-symbol resolution contracts;
- CSV provider;
- mock provider;
- yfinance adapter with explicit adjustment semantics;
- optional Alpaca adapter boundary;
- validation and missing-data rules;
- sample datasets;
- provenance metadata contract;
- `POST /api/v1/market-data/bars/query`;
- shared provider contract tests.

Exit gate:

- identical normalized data shape regardless of provider;
- ordered multi-symbol requests return bars plus per-symbol status;
- deterministic offline sample-data workflow;
- data-quality tests green.

## Phase 3 — Quantitative kernel

Build in `portfolio_engine`:

```text
performance/
  returns
  cumulative return
  CAGR
  rolling returns
  volatility
  Sharpe
  Sortino
  drawdown

risk/
  beta
  correlation
  concentration

portfolio/
  weighted returns
  valuation helpers
  allocation helpers
```

Build mathematical unit tests, property tests, and validation fixtures at the same time.

Exit gate:

- no framework imports in `portfolio_engine`;
- formulas match Section 11;
- independent validation passes.

## Phase 4 — Portfolio ledger, API, and analytics UI

Build:

- Portfolio/Asset/AssetProviderSymbol/Transaction models;
- Django ORM managers/querysets and application services;
- ledger replay and cash accounting;
- TWR;
- holdings service;
- portfolio analytics service;
- `/api/v1` portfolio and analytics endpoints;
- Portfolio Dashboard;
- Portfolio Analysis pages;
- Market Data Explorer with ticker-list input;
- shared ECharts foundation and theme;
- ECharts multi-symbol price comparison and candlestick/volume views;
- CSV transaction import;
- sample portfolio workflow.

Release:

- **v0.1.0 — Portfolio Analytics**

Exit gate:

- v0.1 criteria from Sections 23.2–23.4 satisfied.

## Phase 5 — Optimization and rebalancing

Build:

```text
optimization/
  expected returns
  covariance
  constraints
  minimum variance
  maximum Sharpe
  efficient frontier

rebalancing/
  target weights
  drift
  simulated trades
  schedule rules
  threshold rules
```

Add Allocation Lab and Rebalancing Lab.

Release:

- **v0.2.0 — Portfolio Optimization**

Exit gate:

- Sections 23.5–23.6 satisfied;
- optimization validation suite green.

## Phase 6 — Backtesting / Strategy Lab

Build:

```text
backtesting/
  engine
  strategy context
  portfolio state
  order intents
  execution
  fees/slippage
  result metrics

strategies/
  buy_hold
  moving_average
  momentum
```

Add persisted backtest runs and Strategy Lab UI.

Anti-look-ahead tripwire tests are mandatory during initial engine construction, not after the engine is considered complete.

Release:

- **v0.3.0 — Public MVP / Strategy Lab**

Exit gate:

- all Section 23 requirements satisfied.

## Phase 7 — Hardening and portfolio-quality presentation

Build/improve:

- performance profiling;
- background workers where justified;
- caching;
- accessibility;
- error/warning UX;
- demo datasets;
- screenshots/video;
- expanded architecture documentation;
- coverage reporting;
- release automation.

This phase exists specifically to make the repository an engineering portfolio piece rather than only a functioning prototype.

## Phase 8 — Grounded AI Portfolio Analyst

Only after the deterministic MVP is stable:

- analytical tool registry;
- intent/tool routing;
- structured insight schemas;
- grounded explanations;
- prompt-injection/data-boundary tests where external text is later introduced;
- explicit unsupported-question behavior.

Release target:

- **v0.4.0 — AI Portfolio Analyst**

---

# 25. Change Control and Amendments

## 25.1 Baseline rule

**Status: NORMATIVE**

This document is a clean unified baseline. Architectural or mathematical behavior MUST NOT be changed merely because generated code, a library default, or a developer preference differs from this guide.

## 25.2 Amendment process

**Status: NORMATIVE**

A deliberate change to a NORMATIVE requirement SHALL be proposed as a numbered amendment under:

```text
docs/amendments/
```

Naming convention:

```text
0001-short-description.md
0002-short-description.md
...
```

An amendment SHOULD contain:

1. problem statement;
2. affected guide sections;
3. current behavior;
4. proposed behavior;
5. rationale;
6. migration/compatibility impact;
7. test changes;
8. acceptance criteria.

Once accepted, the amendment SHOULD be merged coherently into the next guide version. The integrated guide then becomes authoritative; standalone amendments remain historical rationale rather than competing specifications.

## 25.3 Mathematical changes

**Status: NORMATIVE**

Any change to a canonical formula, annualization convention, data-alignment rule, backtest execution timing, or cost model MUST include:

- a guide amendment;
- updated unit tests;
- updated independent validation tests;
- release-note disclosure if users could observe changed historical results.

## 25.4 AI-assisted development protocol

**Status: NORMATIVE**

When AI is used to generate or modify project code:

- this guide SHALL be provided or referenced as the authority;
- the AI MUST NOT silently redesign a NORMATIVE contract;
- ambiguity SHOULD result in a proposed amendment or explicitly documented assumption rather than hidden divergence;
- code changes implementing a requirement MUST include corresponding tests;
- generated code MUST remain within the active implementation phase unless a dependency from a later phase is explicitly required;
- the AI SHOULD identify the guide sections implemented or affected by material changes;
- future-looking placeholders MUST not create the appearance that deferred functionality is implemented.

---

# 26. Deferred Scope

**Status: NORMATIVE**

The following are deliberately deferred beyond the public MVP. Their absence is not a defect:

- real brokerage account synchronization;
- order execution;
- options/futures/crypto;
- multi-currency valuation and FX attribution;
- tax lots and tax optimization;
- explicit split/dividend/merger corporate-action engine;
- inflation-adjusted performance;
- factor attribution;
- risk parity;
- Black-Litterman;
- hierarchical risk parity;
- Value at Risk / Conditional VaR;
- Monte Carlo retirement/planning simulations;
- walk-forward parameter optimization;
- parameter-search grids at scale;
- cross-sectional universe selection;
- intraday backtesting;
- market-impact models;
- bid/ask spread simulation;
- live paper trading;
- autonomous trading;
- free-form strategy scripting;
- personalized suitability questionnaires;
- AI-generated trading directives.

Deferred capabilities MAY be added only after the public MVP meets its release gates and the relevant behavior is specified.

---

# 27. Normative Constants

**Status: NORMATIVE**

Initial centralized analytical constants:

```text
TRADING_DAYS_PER_YEAR       = 252
CALENDAR_DAYS_PER_YEAR      = 365.2425
DEFAULT_RISK_FREE_RATE      = 0.0
DEFAULT_MAR_ANNUAL          = 0.0
DEFAULT_COMMISSION_RATE     = 0.0
DEFAULT_SLIPPAGE_RATE       = 0.0
MIN_GENERAL_STAT_OBS        = 30
MIN_BETA_OBS                = 60
MAX_STALE_PRICE_SESSIONS    = 3
MAX_BAR_QUERY_SYMBOLS       = 50
MAX_BAR_QUERY_CALENDAR_DAYS = 7305
MAX_BAR_QUERY_ROWS          = 500000
MARKET_DATA_TIMEOUT_SECONDS = 30
WEIGHT_SUM_TOLERANCE        = 1e-8
OPTIMIZATION_TOLERANCE      = 1e-6
```

Constants SHALL live in one documented engine configuration module rather than being repeated as literals throughout the codebase.

Changing a constant that materially changes historical analytical outputs SHOULD be treated as an analytical behavior change and documented accordingly.

---

# Appendix A — MVP Architectural Invariants

**Status: NORMATIVE**

The following statements SHOULD remain easy to verify throughout development:

1. `portfolio_engine` can be imported and tested without Django, Django REST Framework, PostgreSQL, Redis, or network access.
2. Holdings for an owned portfolio can be reconstructed from the transaction ledger.
3. Market data enters the engine only after normalization.
4. A displayed analytical metric maps to a documented engine calculation.
5. Undefined statistics produce structured null/warnings, not NaN or infinity in APIs.
6. Optimizer success is independently validated after the solver returns.
7. A strategy cannot access market data later than its `as_of` date.
8. A close-based signal cannot execute at the same close in the MVP.
9. Backtest transaction costs are explicit and reproducible.
10. Every persisted analytical run records its assumptions and engine version.
11. The frontend does not reimplement authoritative financial formulas.
12. The AI layer, when introduced, explains engine results rather than replacing the engine.
13. A user-entered ticker is resolved to an internal asset and provider symbol before analytics.
14. yfinance, Alpaca, CSV, and mock data pass the same provider contract.
15. ECharts receives presentation data from canonical API results and does not become a second analytical engine.

---

# Appendix B — Definition of Done for a Quantitative Feature

**Status: NORMATIVE**

A quantitative feature is not done until all applicable items are complete:

- formula/behavior exists in this guide or an accepted amendment;
- implementation is in the correct architectural layer;
- inputs and outputs are typed;
- units and assumptions are documented;
- edge conditions are defined;
- unit tests exist;
- at least one independent validation exists for material mathematics;
- property/invariant tests exist where appropriate;
- API serialization handles undefined/non-finite results safely;
- frontend labels the result correctly;
- warnings are surfaced;
- documentation is updated;
- no look-ahead or future-data dependency is introduced;
- CI passes.

---

# Appendix C — First Implementation Prompt Boundary

**Status: INFORMATIVE**

The first repository-generation task should implement **Phase 1 only**. It should create the monorepo/platform foundation and quality gates without prematurely generating optimization, backtesting, or AI code.

The following task should implement **Phase 2** market-data contracts and adapters. Only after Phase 2 passes should Phase 3 quantitative functions begin.

This sequencing is intentional: it creates stable boundaries before the analytical package grows and makes deviations from the guide easier to identify during AI-assisted development.
