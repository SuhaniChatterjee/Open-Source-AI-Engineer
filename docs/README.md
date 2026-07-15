# OpenSource AI Engineer — Documentation

An AI platform that acts as a software engineer specializing in open-source development: understand any GitHub repository in minutes, discover meaningful contribution opportunities, and prepare high-quality pull requests — always under explicit human approval.

**Status:** Draft (v0.1) · **Last updated:** 2026-07-15

---

## Scope framing: the lean MVP wedge

The full vision spans nine feature areas. To ship something valuable and defensible without drowning in scope — and without the #1 existential risk (low-quality auto-PRs getting the GitHub App flagged as spam) — the docs are written around a **phased wedge**:

- **v1 (MVP):** Repository Intelligence + Repo Chat + Architecture Map. Python/TypeScript repos only. *Understand, don't yet contribute.*
- **v2:** Issue Intelligence + single approved PR generation for **safe categories only** (docs, typos, tests, small-scoped bugs), confidence-gated, full approval workflow.
- **v3+:** Open-source Discovery, Autonomous Contribution Mode (drafts only, never auto-published), Personalization, more languages, scale.

Human approval before any write to GitHub is **mandatory in every phase and is never bypassed.**

---

## Documents

| # | Document | Purpose | File |
|---|----------|---------|------|
| 1 | **Product Requirements (PRD)** | What we're building and why: personas, user stories, feature requirements, MVP scoping, KPIs, user flows, risks. | [PRD.md](PRD.md) |
| 2 | **Technical Requirements (TRD)** | System architecture, tech stack, data model, indexing pipeline, RAG design, provider abstraction, security, infra, API surface. | [TRD.md](TRD.md) |
| 3 | **AI Agent Design** | Multi-agent system: agent graph, per-agent specs, LangGraph orchestration, tools/MCP, memory, provider-agnostic model selection, prompt-injection defense, confidence scoring, evaluation. | [AI-Agent-Design.md](AI-Agent-Design.md) |
| 4 | **GitHub App Design** | App auth model, least-privilege permission scopes, webhook events, onboarding flow, approval-gated write flow, rate limiting, anti-spam, security, ToS compliance. | [GitHub-App-Design.md](GitHub-App-Design.md) |
| 5 | **UI/UX Specification** | UX principles, design system, information architecture, screen-by-screen specs with wireframes, interaction flows, AI-transparency/trust patterns, accessibility. | [UX-Specification.md](UX-Specification.md) |
| 6 | **Development Roadmap** | Phase 0–5 plan, workstreams and task breakdowns, milestones, dependency map, Go/No-Go gates, risk register. | [Development-Roadmap.md](Development-Roadmap.md) |

---

## Suggested reading order

- **New to the project?** → PRD → UX Specification → Roadmap
- **Engineering / architecture?** → TRD → AI Agent Design → GitHub App Design
- **Planning / delivery?** → Roadmap → PRD (MVP scope section)

---

## Product at a glance

**Two components**

- **Web Application** (Next.js / React / TypeScript / Tailwind) — the dashboard: connect GitHub, add AI-provider keys, browse repos, chat about a repo, explore the architecture map, discover issues, review AI-generated code, approve PRs, manage autonomous settings.
- **GitHub App** — integrates via official GitHub APIs: read issues/PRs/discussions/docs, clone repos, and (post-approval) create branches, push commits, and open draft PRs; monitors activity via webhooks.

**Free-first stack**

- Frontend: Next.js, React, TypeScript, Tailwind
- Backend: FastAPI (Python, recommended) · Postgres · Redis
- Parsing: Tree-sitter · LSP · git parsers
- Vector / retrieval: ChromaDB or Qdrant + open embeddings
- AI orchestration: LangGraph · PydanticAI · MCP-compatible tools
- GitHub: OAuth · GitHub App · REST + GraphQL · webhooks

**Bring-your-own inference** — users connect their own provider key (Gemini, OpenAI, Anthropic, OpenRouter, Ollama, Groq, Together AI). The platform is an orchestration layer and pays no inference cost.

---

## North-star metric

**Pull-request acceptance rate.** It gates every advance toward more autonomous behavior: PR generation only unlocks after the understanding layer is genuinely good, and autonomous mode only unlocks after acceptance rate clears a defined threshold (see the Roadmap's Go/No-Go gates).
