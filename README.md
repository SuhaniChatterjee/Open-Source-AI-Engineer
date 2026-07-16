# OpenSource AI Engineer

An AI platform that acts as a software engineer specializing in open-source
development: **understand any GitHub repository in minutes**, discover
meaningful contribution opportunities, and prepare high-quality pull requests —
always under explicit human approval.

> **Status:** MVP vertical slice. The v1 wedge — index a repo → explore its
> architecture → chat with cited answers — is **built and working end-to-end**.
> Discovery, PR generation, and autonomous mode are documented and phased
> (see [`docs/`](docs/)).

---

## What works today

- **Index any public GitHub repo**: shallow clone → Tree-sitter structure-aware
  chunking (Python/TS/JS, with a robust line-based fallback) → embeddings →
  vector store.
- **Architecture map**: a "mental model" of the repo — core modules, detected
  architectural layers, entry points ("start here"), and language mix.
- **Repository chat (RAG)**: ask natural-language questions and get answers
  **grounded in the code with file:line citations**.
- **Bring-your-own AI provider**: mock (offline, zero-config) · OpenAI-compatible
  · Ollama (local). The platform pays for **no** inference.
- **Zero-config local run**: falls back to SQLite + an in-memory vector store +
  offline mock providers, so the whole flow runs with no Docker and no API keys.

## Architecture

```
apps/
  api/            FastAPI backend (Python)
    app/
      providers/  LLM + embedding abstraction (mock | openai | ollama)
      indexing/   cloner, Tree-sitter parser/chunker, architecture mapper
      services/   indexing pipeline, RAG chat, vector store
      api/routes/ health, repositories, chat
      models/     SQLAlchemy models
  web/            Next.js 14 + TypeScript + Tailwind dashboard
infra/            docker-compose (Postgres + Redis + Qdrant)
docs/             PRD, TRD, AI Agent design, GitHub App design, UX spec, roadmap
```

## Quick start

### Option A — zero dependencies (fastest)

Runs on SQLite + in-memory vectors + offline mock AI. Great for a first look.

```bash
# 1. Backend
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL="sqlite:///./dev.db" QDRANT_URL="http://localhost:59999" \
  PYTHONPATH=. uvicorn app.main:app --port 8000
# (unreachable QDRANT_URL -> automatic in-memory vector store)

# 2. Frontend (new terminal)
cd apps/web
npm install
cp .env.local.example .env.local
npm run dev            # http://localhost:3000
```

Open http://localhost:3000 and index e.g. `pallets/click`.

### Option B — full local stack (Docker)

```bash
make infra-up          # Postgres + Redis + Qdrant
make api-install && make api-dev
make web-install && make web-dev
```

### Connect a real AI provider (optional)

Copy `apps/api/.env.example` to `apps/api/.env` and set, for example:

```env
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

or point `LLM_PROVIDER=ollama` at a local Ollama instance. With a real provider
the chat returns fully synthesized answers instead of the extractive mock.

## Background jobs

Indexing, contribution drafting, and publishing run off the request path. Two
modes, chosen by `TASK_BACKEND`:

- **`inline`** (default) — FastAPI BackgroundTasks. Zero-config, non-blocking,
  great for dev. No Redis needed.
- **`celery`** — enqueue to a Redis-backed Celery worker for real horizontal
  scaling. Set `TASK_BACKEND=celery`, run Redis, and start a worker:

```bash
make worker    # celery -A app.worker.celery_app worker (TASK_BACKEND=celery)
```

Or with Docker: `docker compose -f infra/docker-compose.yml --profile worker up`.
Enqueued tasks fall back to running inline if no worker is up
(`CELERY_TASK_ALWAYS_EAGER`), so work is never silently dropped.

## Database migrations

The schema is managed by **Alembic**. The API runs `alembic upgrade head` on
startup, so a fresh database is created (and an existing one upgraded)
automatically — no manual step for normal dev. SQLite uses batch mode so column
changes work there too.

```bash
make migrate                 # apply migrations (alembic upgrade head)
make migration m="add x"     # autogenerate a migration after changing models
make migrate-down            # roll back one revision
make db-stamp                # mark a pre-Alembic DB as up-to-date (one-time)
```

A test (`tests/test_migrations.py`) fails if the models and migrations drift
apart, so a new column can't be shipped without its migration.

## Testing

```bash
cd apps/api && source .venv/bin/activate && PYTHONPATH=. pytest -q
```

## API surface (MVP)

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/v1/health` | Liveness + active providers |
| GET  | `/api/v1/repositories` | List indexed repos |
| POST | `/api/v1/repositories` | Add + index a repo (`{"repo": "owner/name"}`) |
| GET  | `/api/v1/repositories/{id}` | Repo detail |
| GET  | `/api/v1/repositories/{id}/status` | Latest index-job progress |
| GET  | `/api/v1/repositories/{id}/architecture` | Architecture map |
| POST | `/api/v1/repositories/{id}/chat` | Ask a question (returns answer + citations) |
| DELETE | `/api/v1/repositories/{id}` | Remove repo + vectors |

Interactive docs at `http://localhost:8000/docs`.

## Roadmap (phased)

The MVP is the **understanding layer**. Contribution features are deliberately
sequenced behind it — see [`docs/Development-Roadmap.md`](docs/Development-Roadmap.md):

1. **v1 (this):** Repository Intelligence + Chat + Architecture Map.
2. **v2:** Issue Intelligence + single approved PRs for *safe* categories
   (docs/typos/tests), confidence-gated, full human-approval workflow.
3. **v3+:** Discovery engine, Autonomous mode (drafts only), Personalization.

Human approval before any write to GitHub is **mandatory in every phase**.

## Documentation

See [`docs/README.md`](docs/README.md) for the full PRD, TRD, AI Agent design,
GitHub App design, UX specification, and development roadmap.
