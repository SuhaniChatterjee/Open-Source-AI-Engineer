# OpenSource AI Engineer — Product Requirements Document

| Field | Value |
|---|---|
| **Product** | OpenSource AI Engineer (OSAE) |
| **Document** | Product Requirements Document |
| **Version** | 0.1 |
| **Status** | Draft |
| **Owner** | Suhani Chatterjee |
| **Date** | 2026-07-15 |
| **Audience** | Product, Engineering, Design, early collaborators |

---

## 1. Executive Summary

OpenSource AI Engineer is an AI platform that acts as a software engineer specializing in open-source contribution. It compresses the two hardest parts of contributing to open source — *understanding an unfamiliar codebase* and *finding a contribution worth making* — from weeks into minutes, and then helps produce a high-quality pull request under strict human approval.

The product has two components:

1. **Web Application** — a Next.js dashboard where developers connect GitHub, chat with an AI about any repository, explore interactive architecture maps, discover issues matched to their skills, review AI-generated code, approve PRs, and manage autonomous contribution cycles.
2. **GitHub App** — the integration layer built on official GitHub APIs: it reads issues/PRs/discussions/docs, clones repositories, creates branches, pushes commits *only after explicit human approval*, opens draft PRs, and monitors repository activity via webhooks.

**Strategy: a lean wedge, expanded carefully.** v1 (already shipped as a working MVP) is deliberately narrow — Repository Intelligence, Repository Chat, and the Architecture Map, for Python/TypeScript repos of capped size. v2 adds Issue Intelligence and single, approved PR generation for *safe* contribution categories only (docs, typos, tests, small bugs), gated by a confidence score. v3+ adds the Discovery Engine, Autonomous Mode (drafts only, never auto-publish), and Personalization. Every phase keeps one invariant: **no write to GitHub ever happens without explicit human approval.**

**North-star metric: PR acceptance rate.** If maintainers merge what OSAE helps produce, the product is creating value for the whole ecosystem. If acceptance rate dips, we throttle PR volume and do not advance phases. This single metric is both our growth gate and our defense against becoming an AI-spam machine.

**Business model note:** users bring their own AI provider key (Gemini, OpenAI, Anthropic, OpenRouter, Ollama, Groq, Together AI). The platform pays for zero inference, which keeps unit economics flat and removes the incentive to ration quality.

---

## 2. Problem Statement & Motivation

### The problem

Open source runs the world, but contributing to it is brutally front-loaded:

- **Understanding cost is enormous.** A developer landing in an unfamiliar repository faces undocumented architecture, implicit conventions, tribal knowledge in old PR threads, and dependency webs. Studies and anecdote agree: ramping up on a serious codebase takes days to weeks before a first useful change. Most would-be contributors give up here.
- **Finding the right issue is a lottery.** "Good first issue" labels are stale, oversubscribed, or mislabeled. There is no reliable way to match an issue to *your* skills, estimate its real complexity, or know whether the maintainers even want it fixed.
- **First PRs often fail.** Contributions get rejected for violating unwritten conventions, missing tests, touching the wrong abstraction, or duplicating in-flight work — all knowable in advance, but only by insiders.
- **Maintainers are drowning.** The rise of low-effort AI-generated PRs has made maintainers *more* hostile to drive-by contributions, raising the bar for everyone.

### Why now

- LLMs are finally good enough at whole-repo comprehension (with retrieval + structural parsing) to answer "how does this codebase work?" accurately with citations.
- GitHub's App platform provides a sanctioned, auditable, permission-scoped way to act on repositories — no scraping, no impersonation.
- BYO-key inference means a solo/indie team can offer deep AI functionality without carrying inference cost.

### Why us / why this shape

The graveyard of "AI writes your PRs" tools is full of products that optimized for PR *volume*. OSAE inverts this: it optimizes for **understanding first, contribution second, and acceptance above all**. The wedge (repo comprehension) is valuable standalone even if a user never opens a PR — which de-risks the product against the spam backlash and builds trust with maintainers before we ever generate code.

---

## 3. Goals & Non-Goals

### Goals

| # | Goal | Measure |
|---|---|---|
| G1 | Reduce time-to-understanding of an unfamiliar repo from days to **< 15 minutes** | Time from repo connect to first "useful answer" (self-reported + proxy: session depth) |
| G2 | Make OSAE-assisted PRs *better than the median human first-time PR* | **PR acceptance rate ≥ 60%** for v2 safe-category PRs |
| G3 | Keep humans irreversibly in the loop | 100% of GitHub writes preceded by explicit approval; zero un-approved writes, ever |
| G4 | Be maintainer-positive, not maintainer-hostile | Zero repos blocking the GitHub App for spam; maintainer NPS tracked from v2 |
| G5 | Operate at ~zero marginal inference cost | 100% of inference on user-supplied keys or local Ollama |
| G6 | Earn expansion: each phase gated on the previous phase's metrics | Phase-advance criteria in §9 met before any v2/v3 feature ships |

### Non-Goals

- **Not** a general-purpose coding copilot or IDE plugin. OSAE is repo-comprehension and contribution-workflow software, not autocomplete.
- **Not** an autonomous merge bot. OSAE never merges, never publishes a PR without approval, and in autonomous mode produces *drafts only*.
- **Not** a code-hosting or CI platform. GitHub is the system of record; OSAE reads and (with approval) writes through it.
- **Not** trying to maximize PR count. Volume is explicitly *not* a KPI; acceptance rate is.
- **Not** supporting every language at launch. Python and TypeScript only in v1 (see §8).
- **Not** a paid-inference reseller. We do not proxy, mark up, or subsidize model calls.

---

## 4. Target Users & Personas

### Persona 1 — "Priya", the beginner OSS contributor

- **Profile:** CS student / early-career developer, 0–2 years experience. Wants OSS contributions for learning, resume, and community (e.g., aiming at GSoC, Hacktoberfest, or a first dev job).
- **Pain:** Stares at a 4,000-file repo and doesn't know where `main()` is. Picks a "good first issue," discovers it was fixed months ago or requires deep context. Her first PR gets closed with "please read CONTRIBUTING.md."
- **Needs from OSAE:** Guided understanding ("explain this repo like I'm new"), honest complexity ratings on issues, guardrails that stop her submitting something embarrassing, and an approval flow that teaches her *why* the AI made each change.
- **Success looks like:** First merged PR within 2 weeks of signup, and she can explain the change she shipped.

### Persona 2 — "Marcus", the experienced developer exploring a new codebase

- **Profile:** Senior engineer, 8+ years. Evaluates OSS dependencies for work, occasionally contributes fixes upstream when his team hits a bug, sometimes ramps onto internal-but-unfamiliar repos.
- **Pain:** His time is expensive. He doesn't need hand-holding; he needs *speed*: "where is retry logic implemented?", "what pattern do they use for plugins?", "will my fix conflict with the refactor in PR #4812?"
- **Needs from OSAE:** Precise, citation-backed answers to architectural questions; an architecture map he can trust; fast issue triage; PR generation he can heavily edit before approving. Cares about BYO-key (his employer mandates a specific provider) and local Ollama for private repos.
- **Success looks like:** Answers an architectural question in 2 minutes that would have taken 2 hours of grepping; ships an upstream fix in one sitting.

### Persona 3 — "Elena", the open-source maintainer

- **Profile:** Maintains a mid-sized OSS project (5k–50k stars) on nights and weekends. Reviews dozens of PRs a month.
- **Pain:** Flooded with low-quality PRs — increasingly AI-generated slop. Onboarding new contributors is unpaid labor. Good first issues are picked over; complex issues rot.
- **Needs from OSAE:** OSAE-originating PRs must be *clearly labeled*, follow her CONTRIBUTING.md, include tests, and arrive at a sane rate. Ideally OSAE reduces her load: contributors arrive already understanding the codebase, and pre-triaged issue intelligence surfaces what's actually tractable.
- **Success looks like:** OSAE-assisted PRs have a *higher* merge rate than average first-timer PRs; she never has to block the App.
- **Note:** Elena is both a user and a *stakeholder-veto*. If Elenas revolt, the product dies. Maintainer experience is a first-class requirement, not marketing.

### Secondary personas (not designed for in v1–v2, kept in view)

- **Dev-rel / OSPO teams** wanting contribution programs for employees (v3+ B2B angle).
- **Bootcamps/educators** using OSAE as a teaching tool for reading real code.

---

## 5. User Stories / Jobs-to-be-Done

### Repository Intelligence & Chat (v1 — Shipped)

- As a **beginner contributor**, I want to ask "how does authentication work in this repo?" and get an answer with file/line citations, so that I can trust and verify what the AI tells me.
- As an **experienced dev**, I want the index to understand code structure (functions, classes, imports), not just text chunks, so that answers reflect how the code actually fits together.
- As a **beginner**, I want a "getting started" briefing generated from the repo (setup, entry points, conventions, where tests live), so that I skip hours of README archaeology.
- As an **experienced dev**, I want indexing of a mid-sized repo to finish in minutes with visible progress, so that I can start asking questions in the same sitting.

### Architecture Map (v1 — Shipped)

- As an **experienced dev**, I want an interactive map of modules and their dependencies, so that I can see the shape of the system before diving into files.
- As a **beginner**, I want to click a node on the map and jump into a chat scoped to that module, so that exploration and explanation are one motion.

### Issue Intelligence (v2)

- As a **beginner**, I want each issue annotated with estimated complexity, time, risk, and required skills, so that I pick something I can actually finish.
- As an **experienced dev**, I want to see which files an issue likely touches and whether any open PR already addresses it, so that I don't duplicate work.
- As a **maintainer**, I want issue triage signals to be conservative (mark "unclear" rather than guess), so that contributors aren't sent on wild goose chases in my repo.

### AI Software Engineer + Human Approval (v2)

- As a **beginner**, I want the AI to propose a plan before writing code, so that I understand and can redirect the approach.
- As an **experienced dev**, I want to edit the AI's diff before approving, so that the PR is *mine*, not the machine's.
- As a **user of any level**, I want the system to refuse to open a PR when its own confidence is low, so that my GitHub reputation is protected.
- As a **maintainer**, I want every OSAE-assisted PR to disclose AI assistance and link the human approver, so that provenance is honest.

### Discovery Engine (v3)

- As a **beginner**, I want a feed of contribution opportunities across GitHub matched to my languages and interests, so that I don't need to already know which repo to help.
- As an **experienced dev**, I want to filter discovery by "repos my project depends on," so that my contributions serve my own stack.

### Autonomous Contribution Mode (v3)

- As a **power user**, I want OSAE to run a scheduled cycle overnight that *prepares* draft PRs for my review, so that my morning starts with reviewable work instead of a blank page.
- As a **cautious user**, I want autonomous mode to have a hard cap on drafts per cycle and to never publish anything, so that autonomy never becomes exposure.

### Personalization (v3)

- As a **returning user**, I want OSAE to learn my languages, review style, and rejected-suggestion patterns, so that proposals fit me better over time.

### Provider Flexibility (v1 — Shipped)

- As a **user**, I want to plug in my own Gemini/OpenAI/Anthropic/OpenRouter/Groq/Together key or point at local Ollama, so that I control cost, privacy, and model choice.
- As a **privacy-sensitive user**, I want my API keys stored encrypted and never logged, so that connecting a key is safe.

---

## 6. Feature Requirements

Priorities: **P0** = must exist for its phase to ship; **P1** = important, can trail the phase by a release; **P2** = valuable, schedule when capacity allows.

### 6.1 Repository Intelligence Engine — P0, v1 — **Shipped (MVP)**

**Description:** The foundation. Builds a semantic knowledge graph of a repository: source structure via Tree-sitter parsing (functions, classes, imports, call relationships), documentation, dependency manifests, and conventions — indexed for retrieval.

**Functional requirements**

- FR-1.1 — Index any public GitHub repo (and private repos the user's GitHub App installation grants) in Python and TypeScript. *(Shipped)*
- FR-1.2 — Structural parsing with Tree-sitter: extract symbols, definitions, imports, and file-level relationships; store alongside embedded chunks. *(Shipped)*
- FR-1.3 — Enforce repo-size cap (files/LOC/total bytes) with a clear pre-index estimate and friendly rejection above cap. *(Shipped)*
- FR-1.4 — Incremental re-index on new commits (webhook-triggered), reprocessing only changed files. *(P1, partial — full re-index shipped; incremental is v1.x)*
- FR-1.5 — Index docs (README, CONTRIBUTING, /docs), dependency manifests (pyproject/package.json), and CI config as first-class retrievable sources.
- FR-1.6 — Per-repo index isolation; deleting a repo connection purges its index within 24h.

**Acceptance criteria**

- A 50k-LOC Python or TS repo indexes end-to-end in ≤ 5 minutes on standard infrastructure, with visible progress states (queued → cloning → parsing → embedding → ready).
- Retrieval for a symbol-level question ("where is `RateLimiter` defined?") returns the correct file+line in top-3 results ≥ 95% of the time on the internal eval set.
- Repos over the cap are rejected *before* cloning completes, with the cap stated.

### 6.2 Repository Chat Assistant — P0, v1 — **Shipped (MVP)**

**Description:** Conversational interface over the knowledge graph. RAG chat that answers questions about architecture, conventions, "how do I X in this repo," with inline citations to files and lines.

**Functional requirements**

- FR-2.1 — Every substantive claim in an answer carries a citation (file path + line range) linking to the source on GitHub. *(Shipped)*
- FR-2.2 — Streaming responses; conversation history per repo. *(Shipped)*
- FR-2.3 — Uses the user's configured provider/model; graceful, actionable errors on provider failures (bad key, rate limit, model unavailable). *(Shipped)*
- FR-2.4 — "I don't know" behavior: when retrieval confidence is low, say so explicitly rather than hallucinate. *(P0)*
- FR-2.5 — Suggested starter questions generated per repo ("How is the CLI wired to the core library?"). *(P1)*
- FR-2.6 — Scoped chat: start a conversation scoped to a module/directory selected from the architecture map. *(P1)*

**Acceptance criteria**

- ≥ 90% of answers on the internal QA eval set contain at least one valid citation; cited lines actually support the claim on manual audit.
- Zero answers fabricate file paths that don't exist in the repo (hard check post-generation).
- Median time-to-first-token < 3s on a healthy provider.

### 6.3 Intelligent Repository Mapping (Architecture Map) — P0, v1 — **Shipped (MVP)**

**Description:** Interactive visual map of the repository: modules/packages as nodes, imports/dependencies as edges, sized/colored by salience (LOC, churn, centrality).

**Functional requirements**

- FR-3.1 — Auto-generate module-level dependency graph from the parsed index; render interactively (zoom, pan, select). *(Shipped)*
- FR-3.2 — Node detail panel: description, key files, inbound/outbound dependencies, entry into scoped chat. *(Shipped basic; scoped-chat link P1)*
- FR-3.3 — Collapse/expand by directory depth so 1,000-module repos remain legible. *(P1)*
- FR-3.4 — Highlight "hot paths": most-imported modules, entry points, test roots. *(P1)*
- FR-3.5 — Exportable (PNG/SVG) map. *(P2)*

**Acceptance criteria**

- Map renders in < 3s for repos at cap; interaction stays > 30fps.
- Graph edges verifiably correspond to real imports (spot-check tooling; zero fabricated edges).
- New-user comprehension test: after 5 minutes with map + chat, users can correctly name the repo's entry point and 3 core modules ≥ 80% of the time (moderated study, n≥10).

### 6.4 Issue Intelligence — P0, v2

**Description:** Analysis layer over a repo's open issues: estimated complexity, time-to-complete, risk, required skills, likely-touched files, duplicate/in-flight detection, and staleness signals.

**Functional requirements**

- FR-4.1 — For each open issue: complexity rating (trivial/easy/moderate/hard/unclear), estimated effort band, risk level, and required skills — each with a one-line rationale.
- FR-4.2 — "Likely touched files" prediction linking issue text to the knowledge graph.
- FR-4.3 — Conflict detection: flag issues already addressed by an open PR or recent commit.
- FR-4.4 — Staleness signals: last maintainer activity, whether the issue is assigned, label semantics.
- FR-4.5 — Conservative default: when signal is weak, output "unclear — needs maintainer clarification," never a confident guess.
- FR-4.6 — Safe-category classifier: tags issues as SAFE (docs, typos, tests, small well-scoped bugs) vs NOT-SAFE; only SAFE issues are eligible for v2 PR generation.

**Acceptance criteria**

- On a labeled eval set of 200 issues, complexity rating within one band of expert judgment ≥ 75% of the time; "unclear" used, not abused (< 30% of issues).
- Safe-category classifier precision ≥ 90% (an issue tagged SAFE truly is low-risk); recall is sacrificed for precision, deliberately.
- Duplicate/in-flight detection catches ≥ 80% of issues with an obviously linked open PR.

### 6.5 AI Software Engineer — P0, v2 (safe categories only)

**Description:** Given an approved issue, produces a plan, edits files on a branch, writes/updates tests, runs the test suite, and prepares a PR — all in a sandbox, all pending human approval.

**Functional requirements**

- FR-5.1 — Plan-first: generates a numbered implementation plan the user must approve before any code is written.
- FR-5.2 — Executes edits in an isolated sandbox clone; never touches the user's machine or the upstream repo directly.
- FR-5.3 — Runs the repo's test suite (and linters/formatters detected from repo config) in the sandbox; a failing suite blocks the PR from being proposed.
- FR-5.4 — Confidence gate: the system self-scores (tests pass, diff size, category safety, retrieval grounding); below threshold, it declines and explains why instead of proposing a PR.
- FR-5.5 — v2 hard limits: SAFE categories only; single-issue, single-PR flow; diff-size cap (e.g., ≤ 300 changed lines) — anything larger is refused in v2.
- FR-5.6 — Conforms to repo conventions: reads CONTRIBUTING.md, PR templates, commit-message conventions, and code style from the index; PR body follows the repo's template.
- FR-5.7 — Every generated PR body discloses AI assistance and names the approving human.

**Acceptance criteria**

- Zero PRs proposed with a failing sandbox test suite.
- 100% of generated PRs include disclosure text and follow the repo PR template when one exists.
- Confidence gate demonstrably declines: on the internal eval set, ≥ 95% of deliberately-hard seeded issues are declined rather than attempted.
- North-star gate: acceptance rate of v2 PRs ≥ 60% over a rolling 60-day window before any v3 feature ships.

### 6.6 Human Approval Workflow — P0, every phase (v2 for code writes) — **partially Shipped (approval-gated writes are a v1 architectural invariant)**

**Description:** The trust spine of the product. A review UI where users inspect plans, diffs, and test results, request changes, edit directly, and give explicit approval before any GitHub write.

**Functional requirements**

- FR-6.1 — **Invariant:** no branch push, commit to remote, PR creation, or comment happens without an explicit, logged, per-action human approval. No batch "approve all." This invariant is enforced in the GitHub App layer, not just the UI.
- FR-6.2 — Diff review UI: side-by-side/unified diff, per-file approve, inline comments to the AI ("use the existing helper here"), and direct manual editing of the diff before approval.
- FR-6.3 — Approval audit log: immutable record of who approved what, when, with the exact diff hash.
- FR-6.4 — Revocation: user can convert any OSAE-opened PR to closed/draft from the dashboard in one click.
- FR-6.5 — Re-review on change: if the AI revises the diff after feedback, prior approval is voided and re-approval required.

**Acceptance criteria**

- Penetration test / code audit confirms no code path from AI output to GitHub write that bypasses the approval check.
- Audit log reconstructs any PR's full approval chain.
- Median approve-flow time (open review → decision) < 10 minutes for SAFE-category diffs, indicating the UI is actually reviewable.

### 6.7 Open Source Discovery Engine — P1, v3

**Description:** Cross-GitHub discovery: surfaces repositories and issues matched to the user's skills, interests, and dependency graph — the "what should I contribute to?" answer.

**Functional requirements**

- FR-7.1 — Skill profile built from the user's GitHub history (languages, topics) plus explicit preferences; user-editable.
- FR-7.2 — Ranked opportunity feed combining issue intelligence scores, repo health (maintainer responsiveness, merge rates for first-timers), and personal fit.
- FR-7.3 — Filters: language, topic, "my dependencies," time budget, SAFE-only.
- FR-7.4 — Repo-health honesty: repos with hostile-to-newcomer signals (low first-PR merge rate, long response times) are ranked down and labeled.
- FR-7.5 — Respect opt-out: a public registry/mechanism for maintainers to exclude their repos from discovery and from OSAE PR generation; honored absolutely.

**Acceptance criteria**

- ≥ 30% of discovery-feed clicks lead to a repo index or issue analysis (engagement proxy for relevance).
- Maintainer opt-out honored within 24h across discovery, indexing of new users, and PR generation.

### 6.8 Autonomous Contribution Mode — P1, v3 (drafts only)

**Description:** Scheduled cycles in which OSAE selects SAFE issues (from user-approved repos only), prepares plans, code, and tests, and queues **draft PRs and review packets** for the user. It never publishes.

**Functional requirements**

- FR-8.1 — Explicit double opt-in: user enables autonomous mode globally *and* per-repository.
- FR-8.2 — Hard caps: max N prepared drafts per cycle (default 2), max M per repo per week (default 1); caps user-lowerable, not raisable beyond system max.
- FR-8.3 — Output is a review queue in the dashboard; anything not approved within X days is discarded, and staleness (upstream moved) auto-invalidates a prepared draft.
- FR-8.4 — All v2 gates apply (safe categories, confidence gate, tests pass) with *stricter* thresholds than interactive mode.
- FR-8.5 — Kill switch: one click disables all autonomous activity instantly; platform-level global kill switch exists for the operator.
- FR-8.6 — Never opens even a *draft* PR on GitHub without per-PR approval; "draft" in autonomous mode means a locally prepared branch + PR packet awaiting the human, and after approval the PR is opened as a GitHub draft PR by default.

**Acceptance criteria**

- Zero GitHub writes originate from autonomous cycles without a matching approval record.
- Autonomous-prepared PRs maintain acceptance rate ≥ interactive v2 PRs (they face a higher gate, so this should hold; if not, autonomous mode is paused).
- Cycle telemetry (issues considered, declined, prepared) is fully visible to the user.

### 6.9 Personalization Engine — P2, v3

**Description:** Learns from the user's behavior — accepted vs rejected plans, edit patterns on diffs, languages, review comments — to tune future proposals and discovery ranking.

**Functional requirements**

- FR-9.1 — Preference signals: plan approvals/rejections, diff edits, discovery clicks, explicit settings.
- FR-9.2 — Personalization affects *ranking and style*, never safety gates (a user cannot "learn" the system into skipping approval or safety thresholds).
- FR-9.3 — Transparent and resettable: user can view what has been learned and wipe it.
- FR-9.4 — Per-user isolation; no cross-user training on private data.

**Acceptance criteria**

- Plan first-pass approval rate improves ≥ 10 points for users after 10+ interactions vs their own cold-start baseline.
- Documented and verified: safety thresholds are constant regardless of personalization state.

### 6.10 AI Provider Flexibility (BYO key) — P0, v1 — **Shipped (MVP)**

**Description:** Users supply their own inference: Gemini, OpenAI, Anthropic, OpenRouter, Ollama (local), Groq, Together AI. The platform pays for no inference.

**Functional requirements**

- FR-10.1 — Per-user provider configuration with encrypted-at-rest key storage; keys never appear in logs, error messages, or client bundles. *(Shipped)*
- FR-10.2 — Key validation on save ("test connection") with provider-specific error guidance. *(Shipped)*
- FR-10.3 — Model selection per provider; sane defaults per task (chat vs embedding vs codegen). *(Shipped basic)*
- FR-10.4 — Ollama support for fully-local inference paths, enabling private-repo users to keep code off third-party model APIs. *(Shipped)*
- FR-10.5 — Per-task provider routing (cheap model for embeddings, strong model for codegen) — *P1, v2*.
- FR-10.6 — Usage transparency: show the user estimated tokens consumed per operation so BYO cost is predictable. *(P1)*

**Acceptance criteria**

- Security review confirms keys are encrypted at rest, transmitted only over TLS, and absent from logs/telemetry.
- All seven listed providers pass an integration smoke test in CI.
- A user with only an Ollama endpoint can complete the full v1 flow (index → map → chat) with zero external inference calls.

### 6.11 GitHub App & Platform Integration — P0, v1 (read) / v2 (write) — **Shipped (read + OAuth)**

**Description:** The sanctioned integration layer. OAuth for identity, GitHub App installation for repo access, webhooks for activity.

**Functional requirements**

- FR-11.1 — GitHub OAuth sign-in (plus a dev-login path for local development). *(Shipped)*
- FR-11.2 — Minimal-scope permissions: read-only scopes in v1; write scopes (contents, pull requests) requested only when the user enables v2 features.
- FR-11.3 — Webhook ingestion for push/issue/PR events to keep indexes and issue intelligence fresh.
- FR-11.4 — All GitHub interaction via official APIs within documented rate limits; centralized rate-limit budgeting with backoff, never circumvention.
- FR-11.5 — App-attributed actions: PRs opened via the App are attributable and revocable by repo owners through standard GitHub App controls.

**Acceptance criteria**

- v1 installation requests zero write scopes.
- Sustained operation under GitHub secondary-rate-limit rules with zero abuse flags.
- Uninstalling the App severs all access and (per FR-1.6) purges indexes.

---

## 7. MVP Scope vs Later Phases

We are deliberately shipping a *smaller* product than the vision, because the vision's riskiest component (AI-generated PRs at scale) is only viable on top of earned trust and proven comprehension quality. **Understanding is the wedge; contribution is the earned expansion.**

| Phase | Contents | Gate to advance |
|---|---|---|
| **v1 — "Understand" (Shipped as MVP)** | Repository Intelligence Engine, Repository Chat with citations, Architecture Map. Python + TypeScript only. Repo size capped. GitHub OAuth + read-only App scopes. BYO-key providers incl. Ollama. **No GitHub writes at all.** | Activation ≥ 40% (connect → 5+ chat messages), week-4 retention ≥ 20%, citation-validity ≥ 90% on eval set |
| **v2 — "Contribute (safely)"** | Issue Intelligence, safe-category classifier, AI Software Engineer for SAFE issues only (docs/typos/tests/small bugs), confidence gate, diff-size cap, full Human Approval Workflow, write scopes, AI-disclosure in every PR. Single interactive PR flow — no queues, no autonomy. | **PR acceptance rate ≥ 60%** over rolling 60 days AND zero maintainer-spam incidents AND approval-bypass audit clean |
| **v3+ — "Scale (carefully)"** | Discovery Engine with maintainer opt-out registry, Autonomous Mode (drafts only, hard-capped, double opt-in), Personalization Engine, more languages, larger repo caps, per-task provider routing. | Acceptance rate holds ≥ 60% *including* autonomous-prepared PRs; opt-out registry live before discovery launches |

**Opinionated calls (and why):**

- **Two languages only in v1.** Tree-sitter supports dozens; quality per language is what matters. Python + TypeScript covers the largest OSS contributor surface. Breadth waits.
- **Repo-size cap is a feature, not a limitation.** A great experience on 95% of repos beats a degraded experience on monorepos. Raise the cap with evidence, not ambition.
- **SAFE categories in v2 are non-negotiable.** Docs, typos, tests, and small bugs are where AI assistance is unambiguously net-positive and reviewable in minutes. Feature work and refactors are v3-at-earliest, and only if acceptance data supports it.
- **Acceptance rate gates phases.** If maintainers stop merging, we stop expanding — automatically, by policy, not by debate. Volume throttles (per-user and platform-wide PR rate caps) engage if the rolling rate dips below threshold.
- **Autonomous mode never publishes.** "Autonomous" describes preparation, not action. This is permanent product law, not a v3 setting.

---

## 8. Success Metrics / KPIs

### North star

| Metric | Definition | Target |
|---|---|---|
| **PR acceptance rate** | Merged ÷ (merged + closed-unmerged) for OSAE-assisted PRs, rolling 60 days, excluding PRs closed by the author within 1h | **≥ 60%** (v2 gate); ≥ 70% aspiration. **If < 50%: automatic platform-wide PR throttle + phase freeze.** |

### Supporting metrics

| Category | Metric | Definition | Target |
|---|---|---|---|
| Activation | Connect-to-conversation | % of signups who index a repo and send ≥ 5 chat messages in first session | ≥ 40% |
| Activation | Time-to-first-insight | Median time from repo connect to first cited answer | < 10 min (incl. indexing) |
| Comprehension quality | Citation validity | % of answers whose citations support the claim (sampled audit + automated checks) | ≥ 90% |
| Comprehension value | Time-to-understanding | Self-reported "I understand this repo well enough to contribute" survey after session 1 | ≥ 60% agree |
| Engagement | Repos per active user | Median distinct repos indexed per MAU | ≥ 2 |
| Retention | Week-4 retention | % of activated users active in week 4 | ≥ 20% (v1), ≥ 30% (v2) |
| v2 funnel | Issue→PR conversion | % of SAFE-issue analyses that lead to an approved PR | 10–25% (below = not useful; far above = users rubber-stamping) |
| v2 safety | Approval edit rate | % of diffs edited or commented before approval | ≥ 30% (evidence of real review) |
| v2 safety | Confidence-gate decline rate | % of attempted generations declined by the gate | Tracked; sudden drops investigated |
| Maintainer health | Spam signals | App blocks, PRs labeled spam/AI-slop, maintainer complaints | 0 tolerated; any incident triggers review |
| Maintainer health | Maintainer NPS | Survey of maintainers who received OSAE PRs | > 0 by end of v2 |
| Platform | Inference cost to platform | $ of inference paid by the platform | $0 (structural) |

### Anti-metrics (we explicitly do not optimize)

- Total PRs opened. Never a goal, never on a dashboard as a growth number.
- Autonomous-mode utilization. High usage with flat acceptance is a failure mode, not success.

---

## 9. Key User Flows

### Flow A — Onboarding

1. User lands on the web app; signs in with GitHub OAuth (dev-login available in local dev).
2. Consent screen explains exactly what OSAE reads; v1 requests read-only scopes.
3. User configures an AI provider: picks Gemini/OpenAI/Anthropic/OpenRouter/Ollama/Groq/Together, pastes their key (or Ollama URL), clicks "test connection"; key is encrypted and stored.
4. User pastes a repo URL or picks from their GitHub repos; OSAE shows a size estimate against the cap.
5. Indexing runs with live progress (cloning → parsing → embedding → ready).
6. Dashboard opens on the repo with a generated briefing, suggested questions, and the architecture map. **Activation moment:** first cited answer.

### Flow B — Understand a repo (v1 core loop)

1. User opens an indexed repo; reads the auto-generated briefing (purpose, entry points, setup, conventions, test layout).
2. Explores the architecture map; expands the module they care about; opens its detail panel.
3. Asks questions in chat ("where does request validation happen?"); each answer cites files/lines; user clicks a citation to view source on GitHub.
4. Asks follow-ups in-context; optionally scopes chat to a module from the map.
5. Outcome: user can name the entry point, core modules, and the convention set — in minutes, not days.

### Flow C — Discover and contribute (v2/v3 loop)

1. User opens the Issues view for an indexed repo (v2) or the cross-GitHub Discovery feed (v3).
2. Each issue shows complexity, effort band, risk, required skills, likely-touched files, and SAFE/NOT-SAFE tag; in-flight-PR conflicts are flagged.
3. User selects a SAFE issue; OSAE presents a deep analysis: root-cause hypothesis, relevant code (cited), and a proposed plan.
4. User approves, edits, or rejects the plan. Nothing is written until plan approval.
5. On approval, the AI Software Engineer works in a sandbox: edits files, writes/updates tests, runs the suite and linters.
6. If tests fail or confidence is below threshold, OSAE declines with an explanation and the user can redirect or abandon. Otherwise → Flow D.

### Flow D — Approve a PR (the trust moment)

1. User receives a review packet: plan recap, full diff, test results, lint results, confidence score, and the drafted PR title/body (following the repo's template, with AI-assistance disclosure).
2. User reviews the diff file-by-file; can comment inline to request AI revisions, or edit the diff directly.
3. Any AI revision voids prior approval and regenerates the packet for re-review.
4. User clicks **Approve & Open PR** — a single, explicit, logged action.
5. Only now does the GitHub App create the branch, push the commit(s), and open the PR (draft PR by default) under the App's identity with the user as approver of record.
6. OSAE monitors the PR via webhooks: CI results, maintainer comments, and review requests surface in the dashboard; the user can respond (optionally AI-drafted, again approval-gated) or close/convert the PR in one click.

### Flow E — Autonomous cycle (v3, drafts only)

1. User double-opts-in: enables Autonomous Mode globally, then per selected repo; sets caps (≤ system max) and schedule (e.g., nightly).
2. At the scheduled time, OSAE scans opted-in repos for SAFE issues passing *stricter-than-interactive* gates.
3. For up to N issues (default 2/cycle), it prepares full packets — plan, sandboxed diff, passing tests, draft PR text — locally. **No GitHub writes occur.**
4. Morning: the user finds a review queue. Each packet goes through Flow D individually — no bulk approval exists.
5. Approved packets become GitHub draft PRs; ignored packets expire after X days; upstream changes auto-invalidate stale packets.
6. All cycle telemetry (considered, declined + why, prepared) is visible; one-click kill switch disables the mode instantly.

---

## 10. Constraints & Assumptions

### Constraints

| # | Constraint | Implication |
|---|---|---|
| C1 | **GitHub ToS & anti-spam norms.** GitHub actively moderates automated/low-quality PR activity; maintainer culture is hostile to AI slop. | All writes human-approved and disclosed; volume caps; opt-out registry; App-attributed actions. A single high-profile spam incident could be existential. |
| C2 | **GitHub API rate limits** (App installation limits, secondary limits, search limits). | Centralized rate budgeter, webhook-driven freshness over polling, backoff everywhere. Discovery Engine (v3) is the most rate-hungry feature and must be architected around search limits. |
| C3 | **BYO-key cost model.** Users bear inference cost; the platform must run on any of 7 providers. | Provider-agnostic abstraction; token-usage transparency; features must degrade gracefully on weak/cheap models; we cannot assume a frontier model. |
| C4 | **Repo size cap (v1).** Index quality and cost must stay predictable. | Monorepos and giant repos are out of scope until incremental indexing and hierarchical retrieval mature. |
| C5 | **Sandboxed execution.** Running arbitrary repo test suites is running untrusted code. | Isolated, network-restricted, resource-capped sandboxes; no secrets in sandbox env. |
| C6 | **Two languages (v1).** Tree-sitter grammar + eval quality per language gates expansion. | Language expansion is a deliberate, evaluated release, not a config flip. |
| C7 | **Small team / indie economics.** | Ruthless phase discipline; no feature ships without its gate metric instrumented. |

### Assumptions (to validate)

- A1 — Repo comprehension alone (v1) is valuable enough to retain users before any PR features exist. *(Early MVP signal: promising; must be confirmed by retention data.)*
- A2 — Users will supply their own API keys; key friction won't kill activation. Ollama and free-tier providers (e.g., Gemini free tier, Groq) are the mitigation.
- A3 — Maintainers will tolerate — and eventually welcome — clearly disclosed, high-quality, human-approved AI-assisted PRs. This assumption is the whole ballgame for v2; we test it with a small allowlist of friendly repos first.
- A4 — RAG + Tree-sitter structural grounding keeps hallucination low enough that citations stay ≥ 90% valid as repos scale toward the cap.
- A5 — The SAFE-category boundary (docs/typos/tests/small bugs) is machine-classifiable with ≥ 90% precision.
- A6 — PR acceptance rate is measurable reliably (webhook access to PR outcomes persists even when maintainers don't interact with the App).

---

## 11. Risks & Mitigations

| # | Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|---|
| R1 | **Spam/quality backlash (existential).** OSAE PRs are perceived as AI slop; maintainers block the App, publicize it, GitHub sanctions it. The product's reputation dies before its metrics do. | Existential | Medium | Acceptance-rate north star with **automatic throttle** below 50%; SAFE-categories-only in v2; confidence gate that declines; mandatory human approval + edit-friendly review UI; AI disclosure in every PR; per-user and platform-wide volume caps; maintainer opt-out registry live before discovery; launch v2 with an allowlist of consenting repos; maintainer NPS tracked as a first-class metric. |
| R2 | **Comprehension hallucination erodes trust.** Wrong-but-confident answers about a repo poison the wedge value. | High | Medium | Citations mandatory + automated path-existence checks; low-confidence → explicit "I don't know"; per-repo eval harness; structural (Tree-sitter) grounding, not text-only RAG. |
| R3 | **GitHub platform risk.** API/policy changes, App suspension, rate-limit tightening. | High | Low–Med | Official APIs only; minimal scopes; conservative rate budgeting; direct line to GitHub developer relations before v2 write-scope launch; architecture keeps a degraded read-only mode viable. |
| R4 | **BYO-key friction kills activation.** Users bounce at "paste your API key." | Medium | Medium | Ollama/local path; free-tier provider guides in onboarding; "test connection" UX; possible future sponsored starter credits (explicitly not inference resale). |
| R5 | **Sandbox escape / supply-chain attack.** Malicious repo code executes during test runs. | High | Low | Network-isolated, resource-capped sandboxes; no secrets in sandbox; ephemeral environments; treat every repo as hostile. |
| R6 | **User API-key compromise.** Key leak via logs, client, or breach. | High | Low | Encryption at rest, TLS in transit, log-scrubbing, key redaction tests in CI, minimal key surface area, security review before each phase launch. |
| R7 | **Weak-model degradation.** On cheap/small models, codegen quality craters and drags acceptance rate down. | Medium | Medium | Per-task minimum-capability recommendations; confidence gate is model-output-based (tests, grounding) not model-trust-based; warn users when configured model underperforms on internal benchmarks. |
| R8 | **Duplicate/conflicting contributions.** OSAE users pile onto the same popular SAFE issues. | Medium | Medium | In-flight-PR conflict detection (FR-4.3); cross-user claim awareness within the platform; discovery ranking diversifies. |
| R9 | **Legal/licensing ambiguity.** AI-generated code provenance, repo license compliance (e.g., contributing GPL code patterns across projects). | Medium | Low–Med | Disclosure in PRs; per-repo license surfaced in UI; no cross-repo code transplantation by design (generation grounded in the target repo); counsel review before v2. |
| R10 | **Phase-discipline erosion.** Internal pressure to ship v3 features before gates are met. | Medium | Medium | Gates written into this PRD (§7) and instrumented in dashboards; phase advancement requires the gate metrics, reviewed explicitly. |

---

## 12. Open Questions

1. **Maintainer opt-out mechanics.** File-based convention in-repo (e.g., `.github/osae.yml`), a hosted registry, or both? Do we also honor generic AI-contribution opt-out conventions if they standardize?
2. **v2 launch allowlist.** Which 10–20 friendly repos/maintainers do we partner with for the first wave of write-enabled usage, and what does that partnership promise them?
3. **PR identity model.** Should PRs be authored by the App bot with the user as co-author, or pushed to the user's fork under their identity with App disclosure? (Reputation, accountability, and ToS trade-offs differ.)
4. **Acceptance-rate measurement edge cases.** How do we count PRs merged manually after being closed, squash-merged with changes, or sitting unreviewed > 90 days?
5. **Embedding provider coupling.** Re-indexing cost when a user switches providers (embeddings aren't portable) — do we re-embed silently, prompt, or maintain a platform-side embedding default?
6. **Private-repo posture.** v1 supports what the App installation grants — but do we *market* private-repo support before SOC2-grade controls exist?
7. **Monetization.** BYO-key removes inference cost but not infra cost. Free tier limits (repos indexed? repo size? autonomous cycles?) vs paid tier — decide before v2, since limits shape architecture.
8. **Repo cap specifics.** The v1 cap needs a published number (files/LOC/bytes) and an upgrade path narrative.
9. **Multi-user/team accounts.** OSPO/dev-rel demand exists — is team functionality a v3 or v4 concern?
10. **Feedback loop to Issue Intelligence.** When maintainers reject an OSAE PR, how do we structurally learn (per-repo memory of maintainer preferences) without storing anything a maintainer would object to?

---

## 13. Out of Scope

The following are explicitly out of scope for this document's horizon (v1–v3):

- **Auto-merge or unapproved publication of any kind** — permanently out of scope, not just deferred.
- **IDE plugins / editor extensions** (VS Code, JetBrains) — the web dashboard is the surface.
- **Non-GitHub forges** (GitLab, Bitbucket, Codeberg, sourcehut) — GitHub only through v3.
- **Languages beyond Python and TypeScript in v1**; expansion is a gated v2+/v3 decision per language.
- **Platform-paid inference, model hosting, or key resale** — BYO-key is structural.
- **Code review of *other people's* PRs as a service** to maintainers — adjacent product, not this one (revisit post-v3).
- **CI/CD execution, deployment, or release management** for target repos.
- **General project management** (roadmaps, sprint boards) for OSS projects.
- **Monorepo-scale indexing** above the published cap (until incremental indexing matures).
- **Fine-tuning models on user or repo data** — retrieval-grounded generation only.
- **Social features** (leaderboards, contributor rankings, gamification) — misaligned with the acceptance-rate ethos; explicitly rejected, not merely deferred, given they incentivize volume.
- **Mobile apps** — responsive web at most.

---

*End of document. Feedback → Suhani Chatterjee. Next revision (0.2) expected after v2 allowlist-partner interviews.*
