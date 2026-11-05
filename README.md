# 🚀 Spec-Driven Development Toolkit (`spec-driven-dev`)

> **Build with specifications, plan with architecture, and implement with autonomous coding agents.**

A modern toolkit designed to bring structured, repeatable **Spec-Driven Development (SDD)** to AI coding agents, with first-class native support for Google **Jetski**, **Antigravity**, **Claude Code**, **Cursor**, **GitHub Copilot**, and **Codex**.

---

## 💡 The Philosophy

> *"Specifications don't serve code — code serves specifications."*

Instead of raw prompts that lead to hallucination, context drift, and brittle hacks, `spec-driven-dev` inverts software development:

1. **The Specification is the Source of Truth**: Requirements, invariants, and acceptance criteria are written and tested first.
2. **Deterministic Gating**: Every phase (Constitution → Specification → Planning → Task Decomposition → Implementation → Convergence) is validated before code is produced.
3. **Autonomous Verification**: Agents don't guess when they're done—they verify against the spec until the system converges.

---

## ✨ Key Features & Architectural Capabilities

### 1. 🏛️ Universal Codebase Knowledge Graph

- **Zero-Dependency Multi-Language AST Engine**: Native AST analysis across 14+ languages (Python, TypeScript, JavaScript, Go, Rust, Java, Kotlin, C/C++, C#, SQL, Protobuf, Prisma, and Jupyter Notebooks) with zero external compilation prerequisites.
- **Embedded SQLite FTS5 Storage**: Local SQLite database stored in `.specify/memory/code-graph.db` with WAL mode and Full-Text Search (FTS5) indexing symbol names, signatures, routes, docstrings, and rich semantic summaries.
- **Recursive CTE Blast Radius Analysis**: Instant dependency graph traversal via recursive SQL Common Table Expressions (CTEs) mapping direct consumers, transitive callers, impacted API routes, affected test suites, and risk levels (`LOW`, `MEDIUM`, `HIGH`).
- **Domain Models & Schemas**: Deep extraction of TypeScript interfaces, type alias objects, Zod schemas, Pydantic models, Go structs, Rust structs, JPA entities, and Prisma tables with declared field names.
- **Interactive Visual Architecture**: Automatic generation of visual Mermaid diagrams (`flowchart TD`) directly from graph edges for instant architectural topology mapping.
- **Sub-50ms Delta Incremental Sync**: SHA-256 content hashing skips unchanged files on subsequent runs, ensuring sub-second updates even on large monorepos.
- **Automation-Ready Stream Output**: Unwrapped raw JSON streams (`--json`) bypass terminal column limits, guaranteeing valid JSON for automated tooling and CI pipelines.

### 2. 🛡️ 100% Recall & Ground-Truth Invariant

- **Dual-Track Discovery**: The Knowledge Graph acts as a Tier 1 structural accelerator for instant symbol lookups and topology analysis, while physical code files, markdown specifications (`spec.md`), and test suites remain the 100% authoritative ground truth.
- **Non-Exhaustive Indexing Principle**: Graph query results are additive starting points (seeds and anchors), **never closed or exhaustive sets**. Even when a graph query returns partial results, agents MUST NOT assume the output represents the complete universe of relevant code. Agents use graph results to locate initial anchor points, then continuously corroborate and expand context through direct file reading, reference tracing, and repository-wide search to guarantee 100% recall.
- **No Negative Assumptions**: Agents are strictly forbidden from concluding a requirement, scenario, or model is missing or unbuilt based solely on graph query results or omissions. If a natural-language scenario or narrative concept does not map to an exact AST identifier, agents seamlessly fall back to holistic grep and direct file inspection.

### 3. 🎯 Full Lifecycle Spec-Driven Workflow

- **Phase 0 — Constitution (`/speckit-constitution`)**: Lock in team standards, architectural invariants, typing conventions, and testing bars before writing code.
- **Phase 1 — Feature Specification (`/speckit-specify`)**: Generate clear, testable specifications with functional requirements, user stories, and measurable success criteria.
- **Phase 1.5 — Socratic Clarification (`/speckit-clarify`)**: Proactively interviews you on up to 5 critical edge cases to eliminate ambiguities before planning.
- **Phase 2 — Architectural Planning (`/speckit-plan`)**: Integrates the knowledge graph to detect existing reusable models, evaluate blast radius on modified modules, and produce `plan.md`, `data-model.md`, and API contracts.
- **Phase 2.5 — Requirements Checklists (`/speckit-checklist`)**: Creates custom, domain-specific verification checklists that act as unit tests for requirements quality.
- **Phase 3 — Dependency Task Breakdown (`/speckit-tasks`)**: Generates an actionable, dependency-ordered `tasks.md` with explicit parallelization markers (`[P]`).
- **Phase 3.5 — Artifact Consistency Analysis (`/speckit-analyze`)**: Non-destructively audits `spec.md` ↔ `plan.md` ↔ `tasks.md` for gaps, orphan tasks, or contradictions before implementation.
- **Phase 4 — Test-Driven Implementation (`/speckit-implement`)**: Builds the feature task-by-task with automated tests, automatically refreshing the code graph upon completion.
- **Phase 5 — Self-Healing Convergence (`/speckit-converge`)**: Directly compares the implemented codebase against all user stories and acceptance criteria in `spec.md`, appending any remaining unbuilt work to `tasks.md` until fully converged.
- **Audit — Zero-Spec Architectural Audit (`/speckit-code-analyze`)**: Generates an instant health audit, coupling hotspot report, and visual Mermaid architecture diagram for any codebase without requiring a feature spec.

### 4. 🤖 Universal AI Agent Native Support

One unified toolkit that adapts natively to your favorite AI coding environment:

- **Google Jetski & Antigravity**: Native skills integration in `~/.gemini/skills/` with instant slash-command discovery in the chat UI.
- **Claude Code**: Native `.claude/` commands and `CLAUDE.md` instructions.
- **Cursor Agent**: First-class `.cursorrules` and workspace skills.
- **GitHub Copilot**: Custom instructions in `.github/copilot-instructions.md`.
- **Windsurf, Codex, Kimi, Kilocode, Bob, & more**: Broad compatibility across 25+ agent formats.

### 5. 🔌 Extensibility & Extension Hooks

- **Hook Lifecycle**: Define pre- and post-execution hooks in `.specify/extensions.yml` (`before_plan`, `after_plan`, `before_implement`, `after_implement`, `before_converge`, etc.) to run custom lints, security scanners, or automated notifications.
- **Catalog Management**: Easily discover and install community extensions and presets with `specify extension list` and `specify extension add`.

---

## ⚡ Quickstart

### 1. Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** package manager

### 2. Install the CLI

Install the tool globally using `uv`:

```bash
uv tool install git+https://github.com/hasanrafiq-goog/spec-driven-dev.git
```

### 3. Initialize in Any Project Directory

Navigate to your project (or an empty folder) and initialize it for your agent:

```bash
# For Google Jetski / Antigravity:
specify init . --integration jetski

# For Claude Code:
specify init . --integration claude

# For Cursor Agent:
specify init . --integration cursor-agent
```

> **Note for Jetski Users**: When initializing with `--integration jetski`, all `/speckit-*` slash commands are automatically linked into `~/.gemini/skills/` so they appear immediately in your chat UI!

---

## 🔄 The SDD Agent Workflow

Run each phase in your agent chat, reviewing outputs along the way:

```text
/speckit-constitution Create principles focused on clean architecture, strict typing, and 100% test coverage.
/speckit-specify Build an asynchronous API health monitoring tool with a live terminal TUI and desktop alerts.
/speckit-plan Use Python 3.12, asyncio, httpx, and Rich for live terminal rendering.
/speckit-tasks
/speckit-implement
/speckit-converge
```

### Slash Commands Reference

| Slash Command | Stage | Purpose |
| :--- | :---: | :--- |
| **`/speckit-constitution`** | 0 | Sets non-negotiable project quality bars, tech stack boundaries, and rules. |
| **`/speckit-specify`** | 1 | Generates the functional specification (PRD, user stories, acceptance criteria). |
| **`/speckit-clarify`** | 1.5 | Active interview mode: agent asks targeted questions to resolve ambiguities before planning. |
| **`/speckit-plan`** | 2 | Designs the architecture, technical dependencies, data models, and interface contracts. |
| **`/speckit-checklist`** | 2.5 | Generates requirements-quality verification checklists. |
| **`/speckit-tasks`** | 3 | Decomposes the plan into discrete, dependency-ordered, agent-executable tasks. |
| **`/speckit-analyze`** | 3.5 | Cross-checks consistency between the spec, plan, and tasks to detect gaps before writing code. |
| **`/speckit-implement`** | 4 | Executes tasks incrementally, running automated tests at each step. |
| **`/speckit-converge`** | 5 | Self-healing verification loop comparing actual code against spec until "Converged". |
| **`/speckit-code-analyze`** | Audit | Standalone architectural health audit, blast radius hotspots, and visual code knowledge graph. |

---

## 🎯 Common User Journeys (CUJs)

### Journey 1: Greenfield Project (Starting from Scratch)

When starting a brand-new project—either from an idea or pre-existing product documentation:

1. **Initialize the workspace**:

   ```bash
   specify init . --integration jetski
   ```

2. **Establish the project constitution**:
   Define non-negotiable tech stack choices, code style, testing bar, and architecture constraints:

   ```text
   /speckit-constitution We build a Next.js 15 app with React Server Components, TypeScript strict mode, Tailwind CSS, and Vitest for testing. All API endpoints must validate input with Zod.
   ```

3. **Ingest requirements or draft the spec**:
   If you have pre-existing PRDs, design documents, or notes, reference or paste them directly:

   ```text
   /speckit-specify Build the MVP described in docs/prd.md with user registration, team workspaces, and role-based permissions.
   ```

4. **Stress-test and clarify ambiguities**:

   ```text
   /speckit-clarify
   ```

   The agent interviews you on up to 5 critical edge cases before designing architecture.

5. **Generate architecture & validate requirements**:

   ```text
   /speckit-plan
   /speckit-checklist
   ```

   `/speckit-plan` designs the system architecture, dependencies, and data schemas. `/speckit-checklist` generates requirements-quality checklists ("unit tests for your requirements") verifying completeness, testability, and edge cases before task breakdown.

6. **Decompose tasks & audit consistency**:

   ```text
   /speckit-tasks
   /speckit-analyze
   ```

   `/speckit-tasks` generates a dependency-ordered task graph. `/speckit-analyze` acts as a quality gate, non-destructively verifying cross-artifact consistency across `spec.md`, `plan.md`, and `tasks.md` to catch coverage gaps or orphaned requirements before writing code.

7. **Implement and converge**:

   ```text
   /speckit-implement
   /speckit-converge
   ```

   The agent builds the project step-by-step with automated tests until the implementation satisfies every acceptance criterion.

---

### Journey 2: Brownfield Project (Existing Codebase Enhancements & Bug Fixes)

When adding a feature or fixing a bug in an existing repository:

1. **Bootstrap Spec Kit into the repo**:

   ```bash
   specify init . --integration jetski
   ```

2. **Analyze existing architecture (zero-spec audit)**:
   Run an initial architectural scan to discover existing endpoints, data schemas, and high-coupling hotspots:

   ```text
   /speckit-code-analyze
   ```

   The agent automatically indexes the repo and renders a visual Code Knowledge Graph and architectural inventory in an interactive UI artifact.

3. **Capture existing repository norms in the constitution**:

   ```text
   /speckit-constitution Align with our existing patterns in src/: FastAPI, SQLAlchemy 2.0, pytest, and 90%+ branch coverage.
   ```

4. **Specify the enhancement or fix**:

   ```text
   /speckit-specify Fix issue where expired JWT refresh tokens cause a 500 error instead of a 401 Unauthorized response in /auth/refresh.
   ```

5. **Plan with codebase context**:

   ```text
   /speckit-plan
   ```

   The agent inspects existing models, database migrations, and routers to design a surgical change that avoids regressions.

6. **Execute and verify**:

   ```text
   /speckit-tasks
   /speckit-analyze
   /speckit-implement
   /speckit-converge
   ```

   The agent breaks work into tasks, audits cross-artifact consistency with `/speckit-analyze`, implements regression tests first, applies the fix, and runs your test suite to ensure green CI.

---

### Journey 3: Mid-Flight Spec Evolution (Handling Missed Requirements)

When you discover mid-way (or after converging) that a requirement was missed or changed:

1. **Update the Spec in-place (do not edit code directly)**:

   ```text
   /speckit-specify We also need a 15-minute expiration window on password reset links and an audit log event written on reset.
   ```

   The agent updates `specs/<feature>/spec.md` with the new requirements without erasing prior context.

2. **Update the plan & append new tasks**:

   ```text
   /speckit-plan
   /speckit-tasks
   ```

   The agent preserves completed tasks (`- [x]`) and appends only the new tasks needed for the requirement change.

3. **Implement remaining work**:

   ```text
   /speckit-implement
   /speckit-converge
   ```

   The agent executes the newly added unchecked tasks and brings the codebase back into full convergence with the updated spec.

---

### Journey 4: Safe Architectural Refactoring

When restructuring complex legacy code without altering business behavior:

1. **Inspect blast radius & coupling hotspots**:
   Before modifying existing modules, examine downstream consumers and routes:

   ```text
   /speckit-code-analyze src/services/billing.py
   ```

2. **Create a characterization spec**:

   ```text
   /speckit-specify Refactor legacy billing calculation service in src/services/billing.py into a modular strategy pattern without changing any existing calculation outputs or API responses.
   ```

3. **Design target architecture and test matrix**:

   ```text
   /speckit-plan
   ```

   Generates a refactoring plan that maps current behavior to the new architecture.

4. **Decompose, build safety harnesses, and execute**:

   ```text
   /speckit-tasks
   /speckit-implement
   /speckit-converge
   ```

   The agent creates comprehensive characterization tests first, refactors module-by-module, and verifies parity against existing test suites.

---

### Journey 5: Codebase Exploration & Architectural Audit (Zero-Spec)

When onboarding onto an unfamiliar codebase, auditing technical debt, or mapping system architecture without building a new feature:

1. **Run whole-codebase analysis**:

   ```text
   /speckit-code-analyze
   ```

   The agent executes a multi-language AST scan, indexes routes/schemas, and creates an interactive UI artifact with a visual Mermaid knowledge graph, API route inventory, and coupling hotspots.

2. **Targeted subsystem deep-dive**:

   ```text
   /speckit-code-analyze auth
   /speckit-code-analyze "how does payment processing work?"
   ```

   The agent traverses the knowledge graph and inspects targeted code slices to map entrypoints, services, database models, and test suites.

---

## 📁 Repository Structure

When initialized, projects store version-controlled artifacts in `.specify/`:

```text
my-project/
├── .specify/
│   ├── memory/
│   │   ├── constitution.md     # Project principles & core guidelines
│   │   ├── code-graph.db       # SQLite knowledge graph database (FTS5 & CTEs)
│   │   └── code-graph.json     # Machine-readable knowledge graph export
│   ├── templates/              # Standard templates for specs, plans, and tasks
│   └── workflows/              # Pipeline definitions
├── specs/                      # Feature specifications & plans
│   └── 001-my-feature/
│       ├── spec.md             # Functional requirements
│       ├── plan.md             # Architecture & technical design
│       ├── data-model.md       # Entity models
│       ├── contracts/          # Interface schemas (JSON Schema, OpenAPI, etc.)
│       ├── tasks.md            # Actionable implementation tasks
│       └── quickstart.md       # End-to-end verification runbook
└── src/                        # Your application source code
```

---

## 🛠️ CLI Utilities

Check environment health:

```bash
specify check
```

Manage extensions:

```bash
specify extension list
specify extension add bug
```

Inspect registered artifacts:

```bash
specify artifact list
```

### 🌐 Codebase Knowledge Graph & Blast Radius

Specify includes a built-in structural knowledge graph that indexes repositories across Web, Backend, Systems, and Data/ML languages (Python, TypeScript/JavaScript, Go, Rust, Java/Kotlin, C/C++, C#, SQL, Protobuf, Prisma, Jupyter Notebooks) with zero external compilation dependencies and sub-50ms incremental caching:

```bash
# Build or incrementally update the codebase graph (SHA-256 delta caching)
specify graph build

# Force a clean full re-scan of the codebase
specify graph build --refresh

# View architectural summary, detected languages, and symbol counts
specify graph summary
specify graph summary --json

# Calculate blast radius, affected routes, and relevant test suites
specify graph blast-radius src/types/simulator.ts
specify graph blast-radius src/models/user.py --max-depth 2 --json

# Discover all HTTP and RPC routes across the codebase
specify graph routes
specify graph routes --json

# Inspect all domain models, database tables, TypeScript interfaces, and schemas
specify graph models
specify graph models --json

# Search code symbols and synthesized docstrings via SQLite FTS5
specify graph query SimulationParameters
specify graph query UserService --limit 10 --json

# Export visual Mermaid flowchart of the architecture
specify graph export --format mermaid
specify graph export --format mermaid --focus src/App.tsx --max-nodes 30
```

---

## 📄 License

MIT License.
