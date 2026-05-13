.PHONY: help migrate migration migrate-down migrate-current migrate-history test

help:
	@echo "Backend Makefile targets:"
	@echo "  make migrate                       — apply pending migrations (alembic upgrade head)"
	@echo "  make migration NAME=\"description\"  — autogenerate a new revision from model diffs"
	@echo "  make migrate-down                  — roll back one revision"
	@echo "  make migrate-current               — show current revision"
	@echo "  make migrate-history               — show full migration history"
	@echo "  make test                          — run pytest"

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

test:
	pytest
