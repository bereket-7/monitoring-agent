.PHONY: install check lint typecheck test eval format compose-up compose-down migrate phase1 docker-check frontend-install frontend-build frontend-lint

install:
	python -m pip install -e ".[dev]"

lint:
	ruff check backend migrations

format:
	ruff format backend migrations

typecheck:
	mypy

test:
	pytest

# Phase 9 regression suite (validators, filters/queries, agent grounding).
eval:
	pytest backend/tests/evaluation -q

check: lint typecheck test

frontend-install:
	cd frontend && npm install

frontend-lint:
	cd frontend && npm run lint

frontend-build:
	cd frontend && npm run build

compose-up:
	docker compose up -d postgres redis

compose-down:
	docker compose down

migrate:
	alembic upgrade head

phase1: compose-up
	@echo "Waiting for Postgres..."
	@docker compose exec -T postgres pg_isready -U postgres -d monitoring_agent
	$(MAKE) migrate
	$(MAKE) check
	@echo "Phase 1 checks passed"

docker-check:
	docker compose up -d postgres redis
	docker compose run --rm --build check
