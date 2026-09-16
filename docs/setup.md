# Portfolio Intelligence — Local Development Setup

This document defines the supported local-development, deterministic demo, and Phase 4/v0.1 release-verification workflows.

The normal development stack is Docker-first:

- PostgreSQL 17;
- Django 5.2 on Python 3.12;
- React/Vite on Node 24;
- normal development settings: `config.settings.dev`;
- deterministic demo/Playwright settings: `config.settings.demo`.

`config.settings.demo` is local-test infrastructure only. It uses SQLite and the committed CSV provider fixtures so browser tests and the v0.1 sample workflow never depend on external provider credentials or network availability.

## Prerequisites

For the Docker-first runtime:

- Git;
- Docker Desktop or Docker Engine with Docker Compose v2;
- GNU Make.

For host-side quality, demo, and browser commands:

- Python 3.12.12;
- `uv` 0.10.0;
- Node.js 24.21.0;
- npm 11.19.0;
- Chromium installed through Playwright.

The repository commits backend and frontend lockfiles. If this batch changes dependencies, regenerate the lockfiles first and commit the generated results:

```bash
make locks
```

Then install the frontend dependencies and browser once:

```bash
cd frontend
npm ci
npm run playwright:install
```

## Normal development startup

Create `.env` from the repository example and use non-production local values only. Do not commit real credentials.

```bash
make bootstrap-env
make up-build
```

The normal development frontend is available on `http://localhost:5173` and the backend on `http://localhost:8000`.

The normal development default market-data provider remains yfinance. The configured development allowlist also permits `mock` and `csv`; provider selection continues to occur on the server.

## Deterministic v0.1 sample portfolio

The sample workflow uses only committed deterministic CSV market data and canonical persisted application models. The seeding command does not store calculated returns, risk metrics, or valuation outputs.

Prepare or refresh the sample database:

```bash
make sample-demo-reset
```

Start the deterministic sample backend:

```bash
make sample-demo-server
```

In a second terminal, start the frontend with the demo backend proxy:

```bash
cd frontend
VITE_DEV_API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5173
```

The intentionally public **local-only** sample credential is:

```text
email:    sample.portfolio@example.test
password: local-demo-password
```

This credential is fixture data, not a secret, and MUST NOT be reused for any deployed account.

The canonical sample portfolio is `Deterministic Sample Portfolio`. It contains canonical AAPL and MSFT holdings, SPY as benchmark, external cash flows, a dividend, a partial sell, and a later buy. Provider mappings use the `csv` provider.

Committed deterministic market-data files live under:

```text
sample_data/portfolio_demo/
```

`NODATA` is intentionally mapped as a canonical CSV-provider asset without a corresponding CSV file. It exists only to prove per-symbol partial-success behavior in the Market Data Explorer.

The demo clock is fixed at September 16, 2026 through `config.settings.demo`. Normal development and production settings continue to use the real application clock.

## Phase 2/Phase 4 market-data evidence

Deterministic offline provider demonstration:

```bash
make market-data-offline-demo
```

Live yfinance smoke test, deliberately outside deterministic CI:

```bash
make market-data-live-smoke
```

The live smoke test requires outbound network access and may fail because of upstream availability or rate limiting; it is operational evidence, not a pull-request CI dependency.

## Playwright v0.1 browser suite

The Playwright configuration starts its own deterministic SQLite-backed Django server and Vite server, flushes the demo database, seeds the sample portfolio, and uses the CSV market-data provider.

Run:

```bash
make e2e
```

or directly:

```bash
cd frontend
npm run test:e2e
```

The suite covers the Phase 4/v0.1 browser flows only. Optimization, rebalancing, and backtesting browser journeys remain deferred to their later release phases.

## Quality and release checks

Run the consolidated deterministic checks:

```bash
make verify
```

Then run browser verification:

```bash
make e2e
```

Regenerate OpenAPI after API-contract changes:

```bash
make openapi
```

### Empty PostgreSQL migration proof

This check is intentionally explicit because it destroys the local Docker database volume:

```bash
docker compose down -v
make up-build
docker compose run --rm backend python manage.py migrate --noinput
docker compose run --rm backend python manage.py migrate --check
```

Do not run the destructive `down -v` sequence against an environment containing data you need to preserve.

## Generated files

`backend/openapi.yaml` is generated with `make openapi`.

`backend/uv.lock` and `frontend/package-lock.json` are generated dependency lockfiles and MUST be committed before CI/release verification:

```bash
make locks
```

The Playwright browser binary is a local/CI runtime dependency and is installed with:

```bash
make playwright-install
```
