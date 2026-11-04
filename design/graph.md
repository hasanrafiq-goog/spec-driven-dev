# Codebase Knowledge Graph Architecture

This document defines the architecture of the Universal Codebase Knowledge Graph in Specify.
It enables agents and developers to build, maintain, and query an architectural graph of
any codebase across languages (Python, TypeScript/JavaScript, Go, Rust, Java/Kotlin, C/C++, C#,
SQL, Protobuf, and Jupyter Notebooks) with zero external compilation dependencies and sub-second
incremental updates.

## Motivation & Goals

In Spec-Driven Development (SDD), especially in brownfield exploration and safe enhancements,
agents need an accurate structural understanding of the codebase:
- **Blast Radius Analysis:** Given a proposed change to a file, model, or function, what downstream
  controllers, routes, services, or test suites are impacted?
- **Route & Model Discovery:** What endpoints (REST, Next.js App Router, gRPC) and data schemas
  (Pydantic, Zod, Protobuf, SQL tables) already exist?
- **Zero Hallucination:** Agents should inspect ground-truth code symbols rather than guessing.
- **Universal & Lightweight:** Pure Python AST and token analysis without requiring external language
  runtimes, Docker containers, or heavy language servers.
- **Incremental Caching:** High-speed updates using SHA-256 and modification timestamps so large
  codebases can be incrementally indexed in milliseconds.

## Component Overview

The Code Graph subsystem is structured into four layers:

1. **Scanner (`scanner.py`):**
   - Respects `.gitignore` rules via `pathspec`.
   - Bypasses build and cache directories (`node_modules`, `.venv`, `dist`, `target`, `__pycache__`, etc.).
   - Discovers all source files matching registered language extensions.
   - Enforces file size limits (`MAX_FILE_SIZE_BYTES = 1MB`) to bypass bundled, minified, or generated blobs.

2. **Parsers (`parsers/`):**
   - `python_parser.py`: Python AST parsing for classes, functions, routes (FastAPI, Flask), models (Pydantic, SQLAlchemy, Dataclass, PyTorch).
   - `web_parser.py`: TypeScript, JavaScript, JSX, TSX, Vue, Svelte parser (Express, Next.js App Router, Zod schemas, interfaces).
   - `go_parser.py`: Go structs, interfaces, methods, functions, Gin/net-http routes.
   - `rust_parser.py`: Rust structs, enums, traits, functions, Actix/Axum routes.
   - `jvm_parser.py`: Java, Kotlin, Scala classes, interfaces, Spring Boot `@GetMapping`/`@PostMapping`.
   - `native_parser.py`: C, C++, C# classes, structs, functions, ASP.NET attributes.
   - `data_ml_parser.py`: Jupyter Notebook code cells, SQL schemas, Protobuf services and messages.

3. **Engine (`engine.py`):**
   - `CodeGraphEngine`: Orchestrates file parsing, incremental hash caching, and symbol extraction.
   - Parallel worker pool (`ThreadPoolExecutor`) for high-throughput initial scans of large repos.
   - Dependency edge resolution: Maps import declarations across files and builds bidirectional dependency graphs.
   - Blast Radius Calculation: Computes direct dependents, transitive downstream graph (depth-bounded), impacted routes, test suites, and risk scores.
   - Local Persistence: Saves the graph to `.specify/memory/code-graph.json`.

4. **CLI Adapter (`commands.py`):**
   - Exposed under `specify graph`:
     - `specify graph build [--refresh] [--workers N]`: Build or incrementally update the graph.
     - `specify graph summary [--json]`: Architectural statistics and language breakdown.
     - `specify graph blast-radius <target> [--max-depth D] [--json]`: Calculate impacted files, routes, and tests.
     - `specify graph routes [--json]`: List all detected HTTP and RPC routes.
     - `specify graph models [--json]`: List all detected data models, tables, and schemas.
     - `specify graph query <symbol> [--limit L] [--json]`: Search for code symbols.

## Scalability on Large Repositories & Monorepos

- **Signatures over Syntax Trees:** Storing only high-level architectural signatures (routes, schemas, symbols, imports) keeps memory and disk usage to ~1–2 KB per source file (~5–10 MB for 5,000 files).
- **Parallel Initial Ingestion:** Multi-threaded parallel workers scale AST extraction across CPU cores.
- **Sub-50ms Incremental Ingestion:** Unchanged files are verified via SHA-256 and skipped instantly.
- **Bounded Traversal:** Blast radius searches use bounded breadth-first traversal (`--max-depth`, default 5) to prevent infinite loops in cyclic dependencies.
- **Context-Window Safety:** Queries emit compact topological slices (under 40 lines of markdown/JSON) rather than dumping full repos into LLM context.

## Tiered Retrieval Strategy

When an agent needs information:
1. **Tier 1 (Graph Structure):** Instant structural retrieval of routes, schemas, models, and blast radius.
2. **Tier 2 (Targeted Code Slices):** Graph provides exact `file_path`, `line_start`, and `line_end`. The agent reads only the precise lines required, preventing context bloat.
3. **Tier 3 (Specs & Semantic Fallback):** For business intent, architectural history, or dynamic metaprogramming not captured in static ASTs, the agent falls back to `specs/`, `docs/`, `ADR/`, or scoped ripgrep searches.

## Search Workflow During `specify plan`

When `specify plan` or `@speckit-plan` is executed:
1. **Architecture Discovery:** Calls `specify graph summary` to identify tech stack and existing frameworks.
2. **Semantic Anchor Search:** Calls `specify graph query <keywords>` to identify models and routes related to the feature.
3. **Blast Radius Analysis:** Calls `specify graph blast-radius <target>` on affected models/services to determine downstream consumers, affected endpoints, and required test suites.
4. **Plan Synthesis:** Populates `plan.md` with factually grounded paths, non-regression test requirements, and exact contract boundaries.
