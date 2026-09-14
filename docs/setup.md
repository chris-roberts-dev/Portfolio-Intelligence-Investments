# Portfolio Intelligence — Local Development Setup

This document defines the local-development and clean-clone workflow for Portfolio Intelligence, including the Phase 2 market-data operational evidence required by the Data Gate.

The development stack is Docker-first:

- PostgreSQL 17.11;
- Django 5.2 on Python 3.12.12;
- React/Vite on Node 24.21.0;
- development settings module: `config.settings.dev`.

The production Django settings module is `config.settings.prod`.

## Prerequisites

Required for the Docker-first runtime:

- Git;
- Docker Desktop or Docker Engine with Docker Compose v2;
- GNU Make if using the repository Make targets.

Required when running quality tools or the Phase 2 market-data evidence commands directly on the host:

- Python 3.12.12;
- `uv`;
- Node.js 24.21.0;
- npm 11.19.0.

Backend and frontend dependency lockfiles are committed and are authoritative for reproducible installs:

- `backend/uv.lock`;
- `frontend/package-lock.json`.

## Environment configuration

Create the local environment file from the committed example:

```powershell
Copy-Item .env.example .env
```

or, where the Make target is supported:

```text
make bootstrap-env
```

Review `.env` before starting services. At minimum, replace placeholder secret values and retain the development settings module:

```text
DJANGO_SETTINGS_MODULE=config.settings.dev
```

Never commit `.env`. `.env.example` contains placeholders only.

## Start the development stack

Build and start PostgreSQL, Django, and the React/Vite frontend:

```text
docker compose up -d --build
```

or:

```text
make up-build
```

Check service state:

```text
docker compose ps
```

Expected development services:

- `db` — healthy;
- `backend` — running;
- `frontend` — healthy.

Start already-built services with:

```text
make up
```

Stop services with:

```text
make down
```

Follow logs with:

```text
make logs
```

## Apply database migrations

Apply all committed migrations inside the Docker Compose network:

```text
docker compose run --rm backend \
  python manage.py migrate --noinput --settings=config.settings.dev
```

Verify no model changes are missing migrations:

```text
docker compose run --rm backend \
  python manage.py makemigrations --check --dry-run --settings=config.settings.dev
```

Verify the Django system configuration:

```text
docker compose run --rm backend \
  python manage.py check --settings=config.settings.dev
```

## Development URLs

Once the stack is running:

- frontend shell: `http://127.0.0.1:5173/`;
- backend health: `http://127.0.0.1:8000/api/v1/health/`;
- OpenAPI schema: `http://127.0.0.1:8000/api/v1/schema/`;
- Swagger UI: `http://127.0.0.1:8000/api/v1/docs/`.

Expected health response:

```json
{
  "status": "ok"
}
```

## Quality commands

### Backend

From the repository root:

```text
make format-check
make lint
make typecheck
make test
```

The corresponding backend checks are:

- Ruff formatting;
- Ruff linting;
- mypy strict type checking;
- pytest.

### Frontend

From `frontend/`:

```text
npm ci
npm run typecheck
npm test
npm run build
```

`npm ci` must use the committed `package-lock.json`. Do not replace deterministic installs with an unlocked dependency update in normal validation.

## Phase 2 market-data operational evidence

The Phase 2 Data Gate includes both deterministic offline evidence and one explicitly invoked bounded live yfinance smoke check.

Neither workflow performs portfolio analytics or later-phase calculations.

### Deterministic offline demonstration

From the repository root:

```text
make market-data-offline-demo
```

Equivalent direct command from `backend/`:

```text
uv run python -m scripts.market_data_offline_demo
```

The command uses only committed CSV sample data and performs no network I/O.

It must preserve this ordered result behavior:

1. `AAPL` — `SUCCEEDED`, 5 bars;
2. `MSFT` — `SUCCEEDED`, 5 bars;
3. `EMPTY` — `NO_DATA`, 0 bars;
4. `UNKNOWN` — `NOT_FOUND`, 0 bars.

The demonstration also proves:

- provider provenance is `csv`;
- interval is `1d`;
- request bounds use inclusive start and exclusive end;
- duplicate requested symbols preserve first-occurrence order and are de-duplicated;
- total output row count is 10;
- `NO_DATA` and `NOT_FOUND` remain explicit per-symbol outcomes rather than being silently dropped.

The deterministic regression test is:

```text
cd backend
uv run pytest -q tests/integration/test_market_data_offline_demo.py
```

### Explicit opt-in live yfinance smoke

The live smoke is manual operational evidence. It is intentionally excluded from normal pytest and pull-request CI.

From the repository root:

```text
make market-data-live-smoke
```

Equivalent direct command from `backend/`:

```text
uv run python -m scripts.market_data_live_smoke
```

The smoke test is deliberately bounded:

- provider: `yfinance`;
- symbols: `AAPL`, `MSFT`;
- start: `2025-01-02` inclusive;
- end: `2025-01-10` exclusive.

A passing run requires both symbols to return non-empty canonical frames and validates:

- ascending, unique canonical bars;
- requested date bounds;
- yfinance source provenance;
- one consistent batch retrieval timestamp;
- the existing canonical market-data validator.

The smoke test performs live external network I/O and can fail because the upstream provider or network is unavailable. A failure is a Phase 2 Data Gate blocker until a successful bounded run is recorded; it must not be hidden by provider fallback.

The smoke command must never be added to normal pull-request CI.

## OpenAPI contract

The generated OpenAPI document is committed at:

```text
backend/openapi.yaml
```

Regenerate and validate it from the Docker backend:

```text
make openapi
```

Then confirm generation produced no unintended contract drift:

```text
git diff --exit-code -- backend/openapi.yaml
```

Do not hand-edit `backend/openapi.yaml`. Change the DRF/drf-spectacular source contract and regenerate the file instead.

## Continuous integration

GitHub Actions runs on pushes and pull requests.

The backend CI job validates:

- frozen installation from `backend/uv.lock`;
- Ruff formatting;
- Ruff linting;
- mypy;
- Django system checks using `config.settings.dev`;
- migration drift;
- migrations against PostgreSQL 17.11;
- pytest;
- OpenAPI generation and drift.

The frontend CI job validates:

- deterministic installation with `npm ci`;
- TypeScript type checking;
- Vitest;
- the Vite production build.

Pull-request CI must not depend on live market-data providers or other external financial-data services. The bounded yfinance smoke is always explicitly invoked outside normal PR CI.

## Clean-clone validation

Use this checklist to prove the repository platform from an empty local environment.

> **Warning:** `docker compose down -v` deletes the development PostgreSQL volume. Use it only when the local development database is disposable.

### 1. Start from a clean repository and Docker state

```text
git status --short
docker compose down -v --remove-orphans
```

`git status --short` should be empty before validation.

### 2. Create local environment configuration

```powershell
Copy-Item .env.example .env
```

Replace placeholder secrets and verify:

```text
DJANGO_SETTINGS_MODULE=config.settings.dev
```

### 3. Build images from committed manifests and lockfiles

```text
docker compose build --pull
```

The build must complete without modifying either lockfile.

### 4. Start PostgreSQL and verify health

```text
docker compose up -d db
docker compose ps
docker compose exec db sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

PostgreSQL must report that it is accepting connections.

### 5. Apply migrations to the empty database

```text
docker compose run --rm backend \
  python manage.py migrate --noinput --settings=config.settings.dev
```

Then verify:

```text
docker compose run --rm backend \
  python manage.py migrate --check --settings=config.settings.dev

docker compose run --rm backend \
  python manage.py makemigrations --check --dry-run --settings=config.settings.dev
```

Expected results:

- all committed migrations apply successfully;
- no unapplied migrations remain;
- no model changes are missing migrations.

### 6. Start the API and frontend

```text
docker compose up -d backend frontend
docker compose ps
```

Required state:

- `db` healthy;
- `backend` running;
- `frontend` healthy.

### 7. Verify API and frontend health

From PowerShell:

```powershell
curl.exe --fail http://127.0.0.1:8000/api/v1/health/
curl.exe --fail http://127.0.0.1:5173/
```

The API must return:

```json
{"status":"ok"}
```

The frontend request must return the Vite-served application document successfully.

### 8. Verify backend quality gates

```text
docker compose run --rm backend ruff format --check .
docker compose run --rm backend ruff check .
docker compose run --rm backend mypy
docker compose run --rm backend pytest -q
```

All commands must exit successfully.

### 9. Verify the deterministic Phase 2 offline market-data workflow

From the repository root:

```text
make market-data-offline-demo
```

The command must complete without network access and produce the ordered `SUCCEEDED`, `SUCCEEDED`, `NO_DATA`, `NOT_FOUND` outcomes documented above with `row_count` equal to 10.

### 10. Verify frontend quality gates

```text
docker compose run --rm frontend npm run typecheck
docker compose run --rm frontend npm test
docker compose run --rm frontend npm run build
```

All commands must exit successfully.

### 11. Verify the committed OpenAPI contract

```text
make openapi
git diff --exit-code -- backend/openapi.yaml
```

Schema generation must validate successfully and produce no diff.

### 12. Confirm the repository remains clean

```text
git status --short
```

The clean-clone validation passes only when the command returns no tracked or untracked build/configuration artifacts other than the intentionally local ignored `.env`.

## Phase 1 completion rule

Phase 1 is not complete merely because individual commands pass in an existing development environment.

The Phase 1 exit gate requires all of the following from a clean clone:

1. documented setup succeeds;
2. PostgreSQL becomes healthy;
3. migrations apply cleanly to an empty database;
4. the Django API starts and `/api/v1/health/` returns HTTP 200;
5. the React frontend starts successfully;
6. backend formatting, linting, typing, and tests pass;
7. frontend type checking, tests, and build pass;
8. generated OpenAPI has no unintended drift;
9. GitHub Actions are green.

## Phase 2 Data Gate operational evidence

The deterministic offline workflow is part of the clean-clone evidence and must pass without network access.

Separately, Phase 2 is not operationally complete until the explicitly invoked bounded live yfinance smoke has succeeded at least once against the current adapter implementation.

The live smoke remains outside normal PR CI so pull requests stay deterministic.