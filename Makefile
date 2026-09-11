COMPOSE := docker compose

.PHONY: bootstrap-env up down logs backend-shell db-shell check lint format-check typecheck test lock

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

db-shell:
	$(COMPOSE) exec db sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

check:
	$(COMPOSE) run --rm backend python manage.py check

lint:
	cd backend && uv run ruff check .

format-check:
	cd backend && uv run ruff format --check .

typecheck:
	cd backend && uv run mypy

test:
	cd backend && uv run pytest -q

lock:
	cd backend && uv lock

openapi:
	$(COMPOSE) run --rm backend python manage.py spectacular --validate --file openapi.yaml