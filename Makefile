COMPOSE := docker compose

.PHONY: bootstrap-env up up-build down logs backend-shell frontend-shell db-shell check lint format-check typecheck test lock frontend-lock locks market-data-offline-demo market-data-live-smoke openapi verify sample-demo-reset sample-demo-server playwright-install e2e v01-release-check v02-release-check createsuperuser

bootstrap-env:
	@test -f .env || cp .env.example .env
	@printf '%s\n' "Review .env and replace placeholder secrets before starting services."

up:
	$(COMPOSE) up -d

up-build:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs --follow

backend-shell:
	$(COMPOSE) run --rm backend sh

frontend-shell:
	$(COMPOSE) run --rm frontend sh

db-shell:
	$(COMPOSE) exec db sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

# ============================
# Check Django Installation
# ============================
check:
	$(COMPOSE) run --rm backend python manage.py check --settings=config.settings.dev

check-migration: 
	$(COMPOSE) run --rm backend python manage.py makemigrations --check --dry-run --settings=config.settings.dev

migration: 
	$(COMPOSE) run --rm backend python manage.py makemigrations --settings=config.settings.dev

migrate: 
	$(COMPOSE) run --rm backend python manage.py migrate --settings=config.settings.dev

lint:
	cd backend && uv run ruff check .

format-check:
	cd backend && uv run ruff format --check .

typecheck:
	cd backend && uv run mypy

test:
	docker compose exec backend uv run pytest -q --ds=config.settings.test

lock:
	cd backend && uv lock

frontend-lock:
	cd frontend && npm install --package-lock-only

locks: lock frontend-lock 

openapi:
	$(COMPOSE) run --rm backend python manage.py spectacular --fail-on-warn --validate --file openapi.yaml

market-data-offline-demo:
	cd backend && uv run python -m scripts.market_data_offline_demo

market-data-live-smoke:
	cd backend && uv run python -m scripts.market_data_live_smoke

verify: 
	@bash scripts/verify.sh

createsuperuser: 
	docker compose exec backend uv run python manage.py createsuperuser --settings=config.settings.dev

sample-demo-reset:
	cd backend && uv run python manage.py migrate --noinput --settings=config.settings.demo
	cd backend && uv run python manage.py seed_sample_portfolio --reset --settings=config.settings.demo

sample-demo-server:
	cd backend && uv run python manage.py runserver 127.0.0.1:8000 --settings=config.settings.demo

playwright-install:
	cd frontend && npm run playwright:install

e2e:
	cd frontend && npm run test:e2e

v01-release-check: verify e2e

v02-release-check: verify e2e
