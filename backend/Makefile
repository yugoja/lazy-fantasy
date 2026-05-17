.PHONY: help db-up db-down migrate migration migrate-down migrate-current migrate-history reset seed test

help:
	@echo "Backend Makefile targets:"
	@echo "  make db-up                         — start local Postgres (Docker)"
	@echo "  make db-down                       — stop local Postgres (Docker)"
	@echo "  make migrate                       — apply pending migrations (alembic upgrade head)"
	@echo "  make migration NAME=\"description\"  — autogenerate a new revision from model diffs"
	@echo "  make migrate-down                  — roll back one revision"
	@echo "  make migrate-current               — show current revision"
	@echo "  make migrate-history               — show full migration history"
	@echo "  make reset                         — drop + recreate local DB, run migrations, seed dev data"
	@echo "  make seed                          — run seed_dev.py (idempotent, safe to re-run)"
	@echo "  make test                          — run pytest"

db-up:
	docker compose -f ../docker-compose.yml up -d postgres

db-down:
	docker compose -f ../docker-compose.yml down

migrate:
	alembic upgrade head

migration:
ifndef NAME
	$(error NAME is required, e.g. make migration NAME="add foo to bar")
endif
	alembic revision --autogenerate -m "$(NAME)"

migrate-down:
	alembic downgrade -1

migrate-current:
	alembic current

migrate-history:
	alembic history

reset:
	docker compose -f ../docker-compose.yml down -v
	docker compose -f ../docker-compose.yml up -d postgres
	@echo "Waiting for Postgres to be ready..."
	@until docker compose -f ../docker-compose.yml exec -T postgres pg_isready -U lazyfantasy -d lazyfantasy_dev > /dev/null 2>&1; do sleep 1; done
	alembic upgrade head
	python -m scripts.seed_dev

seed:
	python -m scripts.seed_dev

test:
	pytest
