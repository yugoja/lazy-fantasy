.PHONY: help up down logs reset

help:
	@echo "Lazy Fantasy — root Makefile"
	@echo ""
	@echo "  make up     — build and start all services (postgres + backend + frontend)"
	@echo "  make down   — stop and remove containers"
	@echo "  make logs   — tail logs for all services"
	@echo "  make reset  — wipe DB volume, restart, run migrations"
	@echo ""
	@echo "Backend-specific targets: see backend/Makefile"

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

reset:
	docker compose down -v
	docker compose up --build -d
	@echo "Waiting for backend to finish migrations..."
	@until docker compose exec -T backend alembic current > /dev/null 2>&1; do sleep 2; done
	@echo "Done. Stack is up at http://localhost:3000"
