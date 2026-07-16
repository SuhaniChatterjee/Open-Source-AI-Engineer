.PHONY: help infra-up infra-down api-install api-dev api-test web-install web-dev dev \
        migrate migration migrate-down db-stamp worker

help:
	@echo "OpenSource AI Engineer — dev commands"
	@echo "  make infra-up      Start Postgres + Redis + Qdrant (docker compose)"
	@echo "  make infra-down    Stop infra"
	@echo "  make api-install   Create venv + install API deps"
	@echo "  make api-dev       Run the FastAPI server on :8000"
	@echo "  make worker        Run a Celery worker (needs Redis; TASK_BACKEND=celery)"
	@echo "  make api-test      Run backend tests"
	@echo "  make migrate       Apply migrations (alembic upgrade head)"
	@echo "  make migration m=\"msg\"  Autogenerate a migration from model changes"
	@echo "  make migrate-down  Roll back one migration"
	@echo "  make db-stamp      Stamp an existing pre-Alembic DB at head"
	@echo "  make web-install   Install frontend deps"
	@echo "  make web-dev       Run the Next.js dev server on :3000"

infra-up:
	docker compose -f infra/docker-compose.yml up -d

infra-down:
	docker compose -f infra/docker-compose.yml down

api-install:
	cd apps/api && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

api-dev:
	cd apps/api && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

worker:
	cd apps/api && . .venv/bin/activate && TASK_BACKEND=celery CELERY_TASK_ALWAYS_EAGER=false \
		celery -A app.worker.celery_app worker --loglevel=info --concurrency=2

api-test:
	cd apps/api && . .venv/bin/activate && PYTHONPATH=. pytest -q

migrate:
	cd apps/api && . .venv/bin/activate && PYTHONPATH=. alembic upgrade head

migration:
	cd apps/api && . .venv/bin/activate && PYTHONPATH=. alembic revision --autogenerate -m "$(m)"

migrate-down:
	cd apps/api && . .venv/bin/activate && PYTHONPATH=. alembic downgrade -1

# For a database created before Alembic (tables already exist): mark it at head
# so `upgrade` won't try to recreate them.
db-stamp:
	cd apps/api && . .venv/bin/activate && PYTHONPATH=. alembic stamp head

web-install:
	cd apps/web && npm install

web-dev:
	cd apps/web && npm run dev
