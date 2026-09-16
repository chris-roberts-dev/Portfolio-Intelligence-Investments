# Portfolio Intelligence Architecture

`docs/dev-guide.md` is the normative authority. This document is a navigation aid for the implemented architecture and does not redefine financial formulas or phase boundaries.

## Runtime layers

The current application follows the required one-way dependency direction:

```text
React/TypeScript presentation
        ↓ REST/JSON
Django REST Framework transport
        ↓
Django application services
        ↓                 ↘
Django ORM                portfolio_engine
        ↓
provider/infrastructure adapters
```

The pure `backend/portfolio_engine/` package owns deterministic quantitative calculations and must not import Django, DRF, settings, database state, HTTP clients, or frontend code. Architecture tests under `backend/tests/architecture/` enforce the most important boundaries.

## Phase 4 application surfaces

- `apps.accounts`: authenticated user/session boundary.
- `apps.assets`: canonical assets and provider-symbol mappings.
- `apps.market_data`: normalized provider-neutral market-bar orchestration.
- `apps.portfolios`: ledger persistence, valuation/performance orchestration, dashboard contracts, analytics, portfolio management, and transaction ingestion.
- `portfolio_engine`: deterministic returns, risk, allocation, attribution, and related kernels.
- `frontend/src`: authenticated presentation and interaction only.

External market-data providers are selected server-side through the provider registry/allowlist. React never instantiates or special-cases a market-data provider.

## Persistence and mutation boundaries

Portfolio holdings are derived from the transaction ledger. Portfolio/transaction mutation workflows use explicit application services and `transaction.atomic()` where multiple persisted records or replay validation are involved. CSV import is atomic and reuses the same canonical transaction/model validation and ledger replay as manual entry.

## Deterministic demo boundary

The v0.1 sample workflow uses `config.settings.demo`, a local SQLite database, a fixed application clock, and committed CSV fixtures under `sample_data/portfolio_demo/`. It exercises normal application/provider/engine boundaries; it does not persist precomputed metrics.

For full normative architecture rules, see Sections 4 and 5 of `docs/dev-guide.md`.
