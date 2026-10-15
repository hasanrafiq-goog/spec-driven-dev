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

---

## 📁 Repository Structure

When initialized, projects store version-controlled artifacts in `.specify/`:

```text
my-project/
├── .specify/
│   ├── memory/
│   │   └── constitution.md     # Project principles & core guidelines
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

---

## 📄 License

MIT License.
