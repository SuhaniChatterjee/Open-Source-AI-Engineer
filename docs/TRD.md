# Technical Requirements Document / System Architecture

**Product:** OpenSource AI Engineer (OSAE)
**Version:** v0.1
**Date:** 2026-07-15
**Status:** Draft

Related documents: [GitHub-App-Design.md](./GitHub-App-Design.md), [AI-Agent-Design.md](./AI-Agent-Design.md), [UX-Specification.md](./UX-Specification.md), [Development-Roadmap.md](./Development-Roadmap.md)

---

## 1. Overview & Scope

OpenSource AI Engineer is an AI platform that understands any GitHub repository, discovers contribution opportunities, and generates high-quality pull requests — always under **mandatory human approval**. It consists of two components:

1. **Web App** — a Next.js dashboard where users connect repositories, chat with codebases, review architecture maps, and (in later versions) approve AI-proposed contributions.
2. **GitHub App** — a first-class GitHub integration using official APIs only: clone repositories, create branches, push commits *only after human approval*, open draft PRs, and receive webhooks.

The platform is **BYO-AI-provider**: users bring their own inference key (Gemini, OpenAI, Anthropic, OpenRouter, Ollama, Groq, Together). The platform pays for zero inference.

### Version scope (lean MVP wedge)

| Version | Scope | GitHub write access |
|---|---|---|
| **v1 (BUILT)** | Repository Intelligence: index a repo, RAG chat with citations, heuristic architecture map. Python/TypeScript only; capped repo size. | None (read-only clone) |
| **v2** | Issue Intelligence: analyze issues, propose fixes for *safe categories* (docs, tests, typed stubs, lint fixes); human-approved PRs via GitHub App. | Branch + draft PR, post-approval only |
| **v3+** | Contribution Discovery across repos, Autonomous cycles (drafts only, never auto-merge), Personalization. | Same gate — approval mandatory forever |

**Non-negotiable invariant:** no write ever reaches GitHub without explicit human approval in the dashboard. This holds in every version, including autonomous modes.

This document describes **the architecture as it exists today (v1, implemented in the monorepo at `opensource-ai-engineer/`)** and the **target architecture** for v2/v3.

---

## 2. Architecture Principles

1. **Free-first.** Every component must run on free tiers or locally. No mandatory paid dependency for development or a small deployment.
2. **BYO inference.** The platform never holds a platform-level LLM bill. Users select a provider and store their own key (encrypted at rest). Mock provider makes the entire system usable offline with zero keys.
3. **Human-in-the-loop, permanently.** AI proposes; humans approve. Every GitHub write (branch push, PR creation) is gated behind an explicit approval action. This is an architectural constraint, not a product setting.
4. **Zero-config local dev with graceful fallbacks.** `SQLite` when Postgres is absent, in-memory vector store when Qdrant is unreachable, mock embeddings/LLM when no key is configured, dev-login when GitHub OAuth is not set up. `docker-compose up` gives the full stack; nothing gives a broken stack.
5. **Security-by-default.** Signed httpOnly session cookies, Fernet-encrypted provider keys, strict per-user tenant scoping (`owner_id`) on all repo/chat routes, and repository content treated as **untrusted data** in every prompt (prompt-injection defense).

---

## 3. High-Level System Architecture

### 3.1 Current (v1, as built)

```mermaid
flowchart LR
    subgraph Client
        WEB["apps/web<br/>Next.js 14 + TS + Tailwind<br/>login / settings / dashboard /<br/>repo (overview · arch map · chat)"]
    end

    subgraph API["apps/api — FastAPI (Python 3.11)"]
        AUTH["Auth routes<br/>GitHub OAuth + dev-login<br/>signed httpOnly cookies"]
        REPOS["Repo routes<br/>owner-scoped CRUD + status"]
        CHAT["Chat route<br/>RAG w/ citations"]
        PROV["Provider routes<br/>settings + encrypted keys"]
        BG["FastAPI BackgroundTask<br/>indexing pipeline"]
        PABS["Provider abstraction<br/>mock / OpenAI-compatible / Ollama"]
    end

    subgraph Data["infra/docker-compose.yml"]
        PG[("Postgres 16<br/>(SQLite dev fallback)")]
        QD[("Qdrant v1.12<br/>(in-memory fallback)")]
        RD[("Redis 7<br/>(provisioned, unused in v1)")]
    end

    GH["GitHub<br/>OAuth + public git clone"]
    LLM["User's LLM provider<br/>OpenAI-compatible / Ollama / mock"]

    WEB -->|"REST /api/v1"| AUTH & REPOS & CHAT & PROV
    AUTH <--> GH
    REPOS --> BG
    BG -->|shallow clone| GH
    BG --> QD
    BG --> PG
    CHAT --> QD
    CHAT --> PABS
    PABS --> LLM
    REPOS & PROV & AUTH --> PG
```

### 3.2 Target-state additions (v2/v3)

```mermaid
flowchart LR
    subgraph Existing["v1 core (unchanged)"]
        WEB["Web App"] --> API["FastAPI API"]
        API --> PG[("Postgres")] & QD[("Qdrant")]
    end

    subgraph New["v2/v3 additions"]
        GHAPP["GitHub App service<br/>installation tokens · webhooks<br/>branch push · draft PRs"]
        WORKERS["Celery workers<br/>indexing · issue analysis ·<br/>PR generation · test runs"]
        SCHED["Scheduler (Celery beat)<br/>autonomous cycles · re-index"]
        SBX["Ephemeral sandbox containers<br/>test execution, no network"]
        RD[("Redis 7<br/>broker + cache")]
    end

    GH["GitHub"]

    API --> RD
    RD --> WORKERS
    SCHED --> RD
    WORKERS --> SBX
    WORKERS --> QD & PG
    GH -->|webhooks: push, issues, PR events| GHAPP
    GHAPP -->|enqueue| RD
    GHAPP <-->|"installation tokens<br/>(least privilege)"| GH
    API -->|"approval gate:<br/>human clicks Approve"| GHAPP
```

Key deltas from v1 to target state:

- **Workers:** indexing moves from in-process `BackgroundTask` to Celery workers backed by the Redis instance already in `docker-compose`.
- **GitHub App service:** a dedicated component holding installation tokens and the *only* code path capable of writing to GitHub — physically downstream of the approval gate.
- **Scheduler:** cron-style autonomous cycles (v3) and webhook-driven incremental re-indexing.
- **Sandbox:** ephemeral containers for running tests against generated patches (v2).

---

## 4. Technology Stack

| Layer | Choice | Rationale | Alternative considered |
|---|---|---|---|
| Backend framework | **FastAPI (Python 3.11)** | Python was chosen deliberately for the AI-engineering ecosystem: **Tree-sitter** bindings, **LangGraph**, **PydanticAI**, and every embedding/LLM SDK are Python-first. FastAPI adds async, OpenAPI docs, and Pydantic validation for free. | Node/NestJS (better JS monorepo cohesion, weaker AI tooling) |
| ORM | **SQLAlchemy 2 (typed, `Mapped[]`)** | Mature, async-capable, single codebase for Postgres and SQLite. | Prisma (Python client immature), raw SQL |
| Database | **Postgres 16** via psycopg; **SQLite** dev fallback | Free tiers everywhere (Supabase/Neon); SQLite keeps local dev zero-config. | MySQL |
| Vector store | **Qdrant v1.12**, per-repo collections; in-memory fallback | Free self-host + generous cloud free tier; payload filtering; per-collection isolation maps cleanly to per-repo tenancy. | pgvector (simpler ops, weaker filtering/HNSW control at scale), Pinecone (not free-first) |
| Code parsing | **Tree-sitter** (Python/TS/TSX grammars) | Structure-aware chunking at function/class granularity; incremental parsing enables future incremental re-index. | Regex/line chunking (used as fallback for md/other) |
| Frontend | **Next.js 14 + TypeScript + Tailwind** | Vercel free tier, file-based routing, SSR where useful; Tailwind for speed. | Vite + React SPA |
| Auth | **GitHub OAuth** (user-to-server) + `itsdangerous`-signed state & session cookies | Users are GitHub users by definition; signed stateless sessions avoid a session store. | Auth0/Clerk (paid, unnecessary) |
| Secrets at rest | **Fernet (cryptography)** | Simple authenticated symmetric encryption for provider keys. | KMS envelope encryption (target for production) |
| Job queue | v1: **FastAPI BackgroundTask**; target: **Celery + Redis 7** | BackgroundTask is zero-infra for the MVP; Redis is already provisioned in compose for the upgrade. | RQ, Dramatiq, arq |
| HTTP client | **httpx** | Async, used directly for OpenAI-compatible APIs — no heavyweight SDK lock-in. | provider SDKs |
| Agent orchestration (v2+) | **LangGraph / PydanticAI** (planned) | Graph-structured agent loops with typed state; the reason Python was chosen. | Custom loop |
| Containerization | **Docker + docker-compose** | One-command local stack; Dockerfile exists for the API. | Nix, devcontainers |

---

## 5. Data Model

### 5.1 Current tables (implemented in `apps/api/app/models/__init__.py`)

All tables inherit `id: String(36)` (UUID) primary key and `created_at`/`updated_at` timestamps from the declarative `Base`.

**users**

| Column | Type | Notes |
|---|---|---|
| id | String(36) PK | UUID |
| github_id | String(64), unique, nullable | GitHub numeric id as string; null for dev-login users |
| login | String(255), indexed | GitHub login |
| name / email / avatar_url | String, nullable | Profile data |
| llm_provider | String(32), default `mock` | `mock` \| `openai` \| `ollama` |
| embedding_provider | String(32), default `mock` | ditto |

**provider_credentials** — unique constraint (`user_id`, `provider`)

| Column | Type | Notes |
|---|---|---|
| id | String(36) PK | |
| user_id | String(36) FK → users.id, CASCADE, indexed | |
| provider | String(32) | e.g. `openai`, `ollama` |
| encrypted_key | Text | **Fernet ciphertext** — plaintext never stored |
| hint | String(64) | masked suffix, safe to display in UI |

**repositories**

| Column | Type | Notes |
|---|---|---|
| id | String(36) PK | |
| owner_id | String(36) FK → users.id, CASCADE, indexed, nullable | tenant scope key |
| full_name | String(255), indexed | e.g. `fastapi/fastapi` |
| clone_url | String(512) | |
| default_branch | String(128), default `main` | |
| status | String(32), indexed | `pending` \| `cloning` \| `parsing` \| `embedding` \| `mapping` \| `ready` \| `failed` |
| languages | Text (JSON) | language → byte share |
| readme_summary | Text, nullable | |
| file_count / chunk_count | Integer | index statistics |
| error | Text, nullable | last failure message |

**index_jobs**

| Column | Type | Notes |
|---|---|---|
| id | String(36) PK | |
| repository_id | String(36) FK → repositories.id, CASCADE, indexed | |
| status | String(32), indexed | `queued` \| `running` \| `succeeded` \| `failed` |
| stage | String(64), nullable | current pipeline stage |
| progress | Integer 0–100 | polled by the web UI |
| log / error | Text, nullable | |

**conversations**

| Column | Type | Notes |
|---|---|---|
| id | String(36) PK | |
| repository_id | String(36) FK → repositories.id, CASCADE, indexed | |
| title | String(255), default `New conversation` | |

**messages**

| Column | Type | Notes |
|---|---|---|
| id | String(36) PK | |
| conversation_id | String(36) FK → conversations.id, CASCADE, indexed | |
| role | String(16) | `user` \| `assistant` |
| content | Text | |
| citations | Text (JSON), nullable | list of `{path, start_line, end_line, score}` |

### 5.2 Planned entities (v2/v3)

| Entity | Purpose | Key fields (sketch) |
|---|---|---|
| **GitHubInstallation** | Maps a GitHub App installation to a user/org; token minting scope | installation_id, account_login, account_type, repositories_selection, suspended_at, user_id FK |
| **ContributionTask** | A discovered/analyzed opportunity (issue, doc gap, test gap) | repository_id FK, source (`issue`/`discovery`/`autonomous`), issue_number, category (`docs`/`tests`/`lint`/`types`), analysis JSON, status (`proposed`→`approved`→`in_progress`→`pr_open`→`done`/`rejected`) |
| **PullRequest** | Tracks an OSAE-generated PR through its lifecycle | task_id FK, repository_id FK, branch, gh_pr_number, gh_url, state (`draft`/`open`/`merged`/`closed`), approved_by (user_id, **required non-null before any push**), approved_at, diff_summary |
| **AutonomousRun** | One scheduled autonomous cycle (v3) | user_id FK, trigger (`cron`/`manual`), started_at, finished_at, tasks_created, budget JSON (token/cost caps), log |
| **PersonalizationProfile** | Per-user contribution preferences (v3) | user_id FK, languages, topics, difficulty, excluded_repos, embedding of past accepted PRs |

Every new table carries a tenant scope column (`user_id` or transitively via `repository_id`) — the owner-scoping rule extends unchanged.

---

## 6. Repository Intelligence Pipeline

### 6.1 Stages as implemented (`apps/api/app/indexing/`, `services/indexing_service.py`)

```mermaid
flowchart TD
    A["POST /repositories<br/>creates Repository + IndexJob"] --> B["1 · Clone<br/>shallow git clone (depth 1)<br/>into temp dir"]
    B --> C["2 · File walk<br/>ignore dirs (.git, node_modules, dist, .venv, …)<br/>caps: ≤ 4000 files, ≤ 400 KB/file<br/>Python/TS/TSX + md/config only"]
    C --> D["3 · Chunking<br/>Tree-sitter structure-aware:<br/>function/class-level for .py/.ts/.tsx<br/>line-window fallback for md/other"]
    D --> E["4 · Embedding<br/>user's embedding provider<br/>batches of 64 chunks"]
    E --> F["5 · Vector upsert<br/>Qdrant per-repo collection<br/>256-point upsert batches<br/>(in-memory store if Qdrant unreachable)"]
    F --> G["6 · Architecture map<br/>heuristics: modules, layers,<br/>entry points, language mix"]
    G --> H["Repository.status = ready<br/>IndexJob: succeeded, progress 100"]

    B & C & D & E & F & G -.->|"stage + progress"| J[("IndexJob row<br/>polled by GET /repositories/{id}/status")]
    B -->|failure at any stage| K["status = failed, error persisted"]
```

Notes on the implementation:

- The whole pipeline runs as a **FastAPI `BackgroundTask`** in the API process (Redis/Celery migration planned — §11). Progress and stage are written to the `IndexJob` row so the UI can poll.
- Chunk payloads carry `path`, `start_line`, `end_line`, and `kind` (function/class/window) — this is what powers citations in chat.
- The clone is discarded after indexing; only chunks + metadata persist.

### 6.2 Planned pipeline extensions

| Extension | Version | Description |
|---|---|---|
| Import / call graphs | v2 | Tree-sitter already yields defs/refs; build per-repo import and call graphs, stored alongside the architecture map |
| Knowledge graph | v2/v3 | Entities (modules, symbols, contributors, issues) + edges (imports, calls, fixes, mentions) to power issue→code localization |
| Incremental re-index on webhook | v2 | GitHub App `push` webhook → diff changed files → re-chunk/re-embed only those files → upsert/delete points by path filter. Avoids full re-clone per commit. |

---

## 7. Retrieval & RAG Design

### As implemented (`apps/api/app/services/chat_service.py`)

1. **Embed the question** with the user's configured embedding provider.
2. **Vector search** scoped strictly to the repository's Qdrant collection (per-repo isolation is also a tenancy boundary): top-k chunks with scores.
3. **Context assembly** — retrieved chunks are concatenated into a context block where each chunk is headed by `[path:start-end (kind)]`, giving the model citable anchors.
4. **System prompt** enforces three rules:
   - **Grounding**: answer only from the provided context; say so when the context is insufficient.
   - **Citations**: reference the `[path:start-end]` anchors used.
   - **Injection defense**: repository content is *data from an untrusted third party* — any instructions appearing inside code/README/comments must be ignored, never followed.
5. **Response** returns the answer plus a structured citations list (`{path, start_line, end_line, score}`), persisted on the `Message` row and rendered as citation chips in the web UI.

With the **mock provider**, answers are extractive (grounded snippets from the retrieved chunks) so the full loop works deterministically offline.

### Planned: hybrid graph retrieval (v2+)

- Combine vector similarity with the import/call graph: seed with vector hits, expand 1–2 hops along graph edges (callers/callees/importers), re-rank by combined score.
- Symbol-name keyword matching (sparse) fused with dense results for identifier-heavy queries.
- Issue→code localization: embed issue text, retrieve, then graph-expand to find the *right file to change*, not just the most similar one.

---

## 8. LLM Provider Abstraction Layer

Location: `apps/api/app/providers/` (`base.py`, `mock.py`, `openai.py`, `ollama.py`, `registry.py`).

### Interfaces

- **`EmbeddingProvider`** — `embed(texts: list[str]) -> list[list[float]]` (+ dimension property).
- **`LLMProvider`** — `complete(system, messages) -> str` (chat completion).

### Implementations

| Provider | Embeddings | LLM | Notes |
|---|---|---|---|
| `mock` | Deterministic hashed bag-of-words, **384-dim** | Extractive grounded answers from retrieved context | Fully offline, zero keys, deterministic for tests |
| `openai` (OpenAI-compatible) | `text-embedding-3-small`-class, **1536-dim** | Chat completions via **httpx** directly (no SDK) | Base-URL configurable → also covers OpenRouter/Groq/Together/Gemini-compat endpoints |
| `ollama` | `nomic-embed-text`-class, **768-dim** | Local models | Free local inference path |

### Per-user resolution

Request → session user → `User.llm_provider` / `User.embedding_provider` → registry constructs the provider, decrypting the API key from `ProviderCredential.encrypted_key` (Fernet) on the fly. Keys exist in plaintext only in request memory.

### Capability caveat — embedding dimensions

Embedding dimensions **differ per provider** (mock = 384, openai = 1536, ollama = 768). A Qdrant collection is created with a fixed dimension, so **switching embedding providers requires re-indexing the repository**. The UI/API must surface this: changing `embedding_provider` invalidates existing collections for that user's repos. (Planned: store the embedding provider + dim on the collection/repo and hard-fail queries on mismatch rather than returning garbage similarity scores.)

Adding a provider = implementing the two interfaces + registering in `registry.py`; no changes elsewhere.

---

## 9. GitHub Integration

### Current (v1): OAuth login only

- **User-to-server GitHub OAuth**: `GET /auth/github/login` returns the authorize URL with an `itsdangerous`-signed `state` (CSRF defense); `POST /auth/github/callback` verifies state, exchanges the code, fetches the profile, upserts the `User`, and sets a signed httpOnly session cookie.
- **Dev-login fallback** (`POST /auth/dev-login`) for zero-config local development, disabled outside dev.
- Repo access in v1 is **read-only public clone** — no GitHub write path exists in the codebase at all.

### Target (v2): GitHub App — see [GitHub-App-Design.md](./GitHub-App-Design.md)

| Aspect | Design |
|---|---|
| Identity | A registered GitHub App; users install it on selected repos. Installation recorded in `GitHubInstallation`. |
| Tokens | Short-lived **installation access tokens** minted per operation from the App's private key (JWT); never stored long-term, scoped to the installation's repos. |
| Permissions (least privilege) | `contents: read/write` (clone, branch, push), `pull_requests: write` (draft PRs), `issues: read`, `metadata: read`. Nothing else — no admin, no workflows, no members. |
| Webhooks | `push` (incremental re-index), `issues`/`issue_comment` (issue intelligence), `pull_request` (track OSAE PR lifecycle). HMAC signature verification mandatory. |
| Write gate | The GitHub App service is the **only** component with write-capable tokens, and its write endpoints require a `PullRequest.approved_by` set by a human in the dashboard. Approval is checked server-side, not trusted from the client. |
| PR style | Always **draft PRs** on a dedicated branch (`osae/<task-id>-<slug>`); never pushes to default branches; never merges. |

---

## 10. Background Jobs & Scheduling

| | Current (v1) | Target (v2/v3) |
|---|---|---|
| Execution | FastAPI `BackgroundTask` in the API process | **Celery workers**, Redis 7 broker (already in docker-compose) |
| Job types | Indexing pipeline only | Indexing, incremental re-index, issue analysis, patch generation, sandboxed test runs |
| Progress | `IndexJob` row (stage/progress/log), polled | Same DB contract kept; add Celery task ids + retries with backoff |
| Scheduling | None | **Celery beat**: cron autonomous cycles (v3) with per-user budgets; periodic stale-index refresh |
| Limits of v1 approach | Jobs die on API restart/redeploy; no concurrency control; one bad job can hog the event loop's thread pool | Worker isolation, per-queue concurrency, task time limits |

The migration is deliberately cheap: the pipeline already communicates exclusively through the `IndexJob` row, so moving it into a Celery task changes the invocation site, not the pipeline.

---

## 11. Code Execution / Sandboxing (v2)

Required before OSAE can claim "the tests pass" for a generated patch.

- **Ephemeral containers** per run: fresh container from a language-pinned base image, repo checked out at the task branch, patch applied, test command executed, container destroyed.
- **Resource limits:** CPU (e.g. 1 vCPU), memory (e.g. 2 GB), wall-clock timeout (e.g. 10 min), disk quota, process count.
- **No network** inside the sandbox (`--network none`); dependencies pre-fetched into a cached layer during a separate, allowlisted install phase.
- **No secrets** ever mounted: no provider keys, no GitHub tokens, no platform env.
- Output = exit code + truncated logs + structured test report; only this crosses the boundary back to the platform.
- Sandbox results are advisory input to the human reviewer — a green sandbox does **not** bypass the approval gate.

---

## 12. Security & Secrets

| Area | Current implementation | Notes / hardening TODO |
|---|---|---|
| Sessions | `itsdangerous`-signed httpOnly cookies; OAuth `state` also signed | TODO prod: `Secure` + `SameSite` flags enforced, key rotation |
| Provider keys | **Fernet encryption at rest** in `provider_credentials.encrypted_key`; only masked `hint` ever returned to the client | TODO prod: real `ENCRYPTION_KEY` from a secret manager (dev fallback key must never ship); consider KMS envelope encryption |
| Tenant isolation | Every repo/chat/provider route filters by `owner_id` from the session — cross-tenant ids 404. Qdrant collections are per-repo, so retrieval cannot cross repos | Keep the scoping rule as a code-review invariant; add tests per new route |
| Prompt injection | Repo content is declared **untrusted data** in the RAG system prompt; instructions found in code/READMEs are to be ignored | v2: same rule for issue text and PR comments (higher-risk surfaces); consider content isolation delimiters + output filters on GitHub-write flows |
| GitHub writes | None exist in v1 | v2: single write path via GitHub App service, server-side approval check, webhook HMAC verification |
| Transport / infra | Local dev over http | TODO prod: HTTPS everywhere, CORS locked to the web origin, rate limiting on auth + chat, dependency audit in CI |
| Dev backdoors | `dev-login` endpoint | Must be hard-disabled by environment flag in production builds |

---

## 13. Scalability & Performance

- **Ingestion caps (v1):** ≤ 4000 files/repo, ≤ 400 KB/file, Python/TS/TSX (+ md/config) only. Caps keep index time and vector cost bounded; they are config values, not constants.
- **Batching:** embeddings in **64-chunk batches**; Qdrant upserts in **256-point batches** — bounds memory and provider-request size.
- **Per-repo collections** keep search space small and deletion O(1) (drop collection).
- **Fallbacks under load:** in-memory vector store is fine for dev but non-persistent — Qdrant required for anything real.
- **Planned:**
  - **Incremental indexing** (webhook-diff based, §6.2) — turns per-commit cost from O(repo) to O(diff).
  - Worker horizontal scaling via Celery queues (indexing vs. chat-adjacent jobs separated).
  - Embedding cache keyed by (provider, model, chunk-hash) to avoid re-embedding unchanged chunks.
  - Raise caps gradually with pagination of file walks and streaming upserts.

---

## 14. Observability

**Current:** structured application logging (uvicorn/FastAPI); pipeline stage + progress + error persisted on `IndexJob` (doubles as a job audit trail); errors persisted on `Repository.error`.

**Planned:**

- **LLM call tracing** — per call: provider, model, latency, prompt/completion token counts, repo/conversation ids (no prompt bodies by default, for privacy). Candidates: OpenTelemetry spans + Langfuse/Phoenix self-hosted (free-first).
- **Per-user cost tracking** — since users pay for inference, show them token usage per repo/conversation and estimated cost per provider price sheet.
- Health/metrics endpoint (`/api/v1/health` exists) → extend with dependency checks (DB, Qdrant, Redis) and Prometheus-format metrics.
- Sentry (free tier) for exception tracking in prod.

---

## 15. Deployment / Infrastructure

Free-first deployment map (all have workable free tiers as of writing):

| Component | Option(s) | Notes |
|---|---|---|
| Frontend | **Vercel** | Native Next.js; free hobby tier |
| Backend API | **Fly.io / Railway / Render** | Dockerfile already exists for `apps/api`; pick per free-tier weather |
| Postgres | **Supabase / Neon** | Managed free Postgres; psycopg URL drop-in |
| Vector DB | **Qdrant Cloud free tier** (1 GB) or self-host on Fly | Per-repo collections fit the free tier for MVP scale |
| Redis (v2) | Upstash free tier / co-located on Fly | Celery broker |
| Local dev | `infra/docker-compose.yml` — Postgres 16, Redis 7, Qdrant v1.12 | Or nothing at all: SQLite + in-memory vectors + mock provider |

CI/CD (planned): GitHub Actions — lint, type-check, `apps/api` tests (pipeline test exists), build images, deploy on tag.

---

## 16. API Surface

All routes under `/api/v1`. 🔒 = requires session cookie; all 🔒 repo/chat routes are owner-scoped.

### Implemented (v1)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/health` | – | Liveness check |
| GET | `/api/v1/auth/config` | – | Which auth modes are available (OAuth configured? dev-login?) |
| GET | `/api/v1/auth/github/login` | – | GitHub authorize URL with signed state |
| POST | `/api/v1/auth/github/callback` | – | Exchange code, upsert user, set session cookie |
| POST | `/api/v1/auth/dev-login` | – | Local dev fallback login (dev only) |
| GET | `/api/v1/auth/me` | 🔒 | Current user profile + provider settings |
| POST | `/api/v1/auth/logout` | 🔒 | Clear session |
| GET | `/api/v1/providers` | 🔒 | Provider status: selected providers + key hints |
| PUT | `/api/v1/providers/settings` | 🔒 | Set `llm_provider` / `embedding_provider` |
| PUT | `/api/v1/providers/keys` | 🔒 | Store a provider key (Fernet-encrypted) |
| DELETE | `/api/v1/providers/keys/{provider}` | 🔒 | Delete a stored key |
| GET | `/api/v1/repositories` | 🔒 | List own repositories |
| POST | `/api/v1/repositories` | 🔒 | Add repo → creates `IndexJob`, kicks pipeline (201) |
| GET | `/api/v1/repositories/{id}` | 🔒 | Repo detail (status, stats, languages) |
| GET | `/api/v1/repositories/{id}/status` | 🔒 | Latest index job: status/stage/progress |
| GET | `/api/v1/repositories/{id}/architecture` | 🔒 | Heuristic architecture map JSON |
| DELETE | `/api/v1/repositories/{id}` | 🔒 | Delete repo + collection (204) |
| POST | `/api/v1/repositories/{id}/chat` | 🔒 | RAG chat → answer + citations |

### Planned (v2)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/github/install` | Redirect to GitHub App installation flow |
| POST | `/api/v1/github/webhooks` | Webhook receiver (HMAC-verified; push/issues/PR events) |
| GET | `/api/v1/repositories/{id}/issues` | Analyzed issues with fix-category classification |
| POST | `/api/v1/repositories/{id}/tasks` | Create a `ContributionTask` from an issue/suggestion |
| GET | `/api/v1/tasks/{id}` | Task detail: analysis, proposed diff, sandbox results |
| POST | `/api/v1/tasks/{id}/approve` | **The human approval gate** — records approver, unlocks GitHub write |
| POST | `/api/v1/tasks/{id}/reject` | Reject with optional feedback (feeds personalization later) |
| GET | `/api/v1/pull-requests` | OSAE-created PRs and their GitHub state |

---

## 17. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Availability | MVP: best-effort single instance; jobs must be resumable/re-runnable after restart (full Celery migration closes the gap) |
| Latency | Chat response start < 10 s on hosted providers (retrieval < 500 ms); index a cap-sized repo < 10 min |
| Cost | Platform infra runs on free tiers at MVP scale; **zero platform inference spend** by construction |
| Privacy | Provider keys encrypted at rest, never logged, never returned unmasked; repo clones ephemeral; prompt bodies not retained in traces by default |
| Safety | No GitHub write without recorded human approval — enforced server-side, in every version |
| Portability | Entire stack runnable offline (SQLite + in-memory vectors + mock provider) with zero external accounts |
| Compatibility | v1 language support: Python, TypeScript/TSX (structure-aware); other text files line-chunked |
| Testability | Mock provider is deterministic so the index→retrieve→answer loop is testable in CI without keys or network |

---

## 18. Technical Risks & Mitigations

| # | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| 1 | **BYO-key friction** — users bounce before configuring a provider | Adoption | High | Mock provider gives a full (if shallow) offline experience; Ollama path for free local inference; one-field key setup with masked hints; Gemini/Groq free tiers documented |
| 2 | Embedding-dimension mismatch after provider switch silently breaks retrieval | Correctness | Medium | Store provider+dim per collection; block queries on mismatch; force explicit re-index (§8) |
| 3 | In-process BackgroundTask jobs lost on deploy/restart | Reliability | High at any real usage | Jobs idempotent + re-runnable from `IndexJob`; Celery/Redis migration scheduled early in v2 |
| 4 | Prompt injection via repo content (and later: issue text) steering the model | Security | Medium | Untrusted-data framing in system prompt (implemented); v2: same for issues/comments, no tool/write capability reachable from RAG context, human approval gate as final backstop |
| 5 | GitHub write bug pushes without approval | Trust-fatal | Low | Single write path in GitHub App service; server-side `approved_by` check; draft PRs on dedicated branches only; audit log; integration tests on the gate |
| 6 | Generated PR quality is low → maintainer backlash, project reputation | Product | Medium | v2 restricts to safe categories (docs/tests/lint/types); sandbox test runs before human review; drafts only |
| 7 | Qdrant free tier / self-host capacity exceeded | Scale | Low (MVP caps) | Per-repo caps; incremental indexing; embedding cache; pgvector as an escape hatch |
| 8 | Provider API drift (OpenAI-compatible is "compatible-ish") | Reliability | Medium | Thin httpx layer per provider, contract tests per provider, base-URL config rather than SDK coupling |
| 9 | Fernet key mismanagement (lost key = all user keys unrecoverable; leaked key = all keys exposed) | Security | Low/High-impact | Prod key from secret manager, rotation procedure (re-encrypt on read), keys are user-replaceable by design |
| 10 | Monorepo API process doing web-serving + jobs + parsing competes for CPU (Tree-sitter is CPU-bound) | Performance | Medium | Caps bound the worst case now; worker split (v2) is the real fix |

---

## 19. Open Technical Questions

1. **Celery vs. lighter queue (arq/Dramatiq)?** Redis is provisioned either way; decide before v2 indexing-load grows.
2. **Knowledge graph storage** — Postgres adjacency tables vs. embedded graph lib vs. dedicated store? Free-first argues for Postgres first.
3. **Chunk-level vs. file-level citations in v2 PRs** — how do we cite evidence inside a generated diff for the reviewer?
4. **Embedding cache keying** — is (provider, model, sha256(chunk)) sufficient, or do we need normalization (whitespace, comments) for hit rate?
5. **Sandbox runtime** — plain Docker with hard limits vs. gVisor/Firecracker? Depends on deployment target (Fly machines vs. self-managed).
6. **Multi-provider single-user** — should a user be able to use different providers per repo (cheap for indexing, strong for chat)? Schema allows it; UX cost unclear.
7. **Rate limiting & abuse** — public-repo indexing is free compute for anyone with an account; per-user repo/index quotas needed before public launch.
8. **Streaming chat responses** — SSE/WebSocket support in the chat endpoint; affects provider abstraction (`complete` → `stream`).
9. **Org-level tenancy** — current model is strictly per-user; GitHub App installations on orgs will force a user↔org membership model earlier than v3 planning assumed.
10. **License/compliance for generated code** — do we need provenance notes in PR descriptions (model, provider) for maintainer transparency? (Leaning yes.)

---

*End of document — v0.1 draft, 2026-07-15.*
