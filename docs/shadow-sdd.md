# Shadow SDD: Non-Polluting Spec-Driven Development

**Shadow SDD** is a repository hygiene workflow designed for teams working in large, shared, or enterprise repositories where committing agent-specific scaffolding (`.specify/`, temporary indexes, local specs) to the primary codebase is restricted or discouraged.

With Shadow SDD, you get the full benefits of:

- **Incremental AST Delta-Caching** (~100ms architectural memory refreshes)
- **Socratic Architectural Gating** (uncompromising domain, API, and schema boundary clarity)
- **Pre-Mutation State Safety Gates** (preventing unintentional file deletions or breaking changes)
- **Task DAG Slicing** (worktree-parallelizable tracer bullets)
- **Bidirectional Traceability Matrix** (requirement-to-code verification)

...all without polluting upstream pull requests or repository git trees.

---

## Operating Modes

### Mode 1: Local Git Exclusion (`.git/info/exclude`)

Keep all Spec Kit state completely local to your workstation or Cloud Workstation without modifying the tracked `.gitignore`:

```bash
# Exclude Spec Kit working directories locally
cat << 'EOF' >> .git/info/exclude
.specify/
specs/
EOF
```

Run Spec Kit commands normally:

```bash
specify init --here
/speckit-code-analyze
/speckit-specify Add order management service
```

Your git status and PR diffs will remain 100% clean of `.specify/` and `specs/` directories.

---

### Mode 2: Monorepo & Out-of-Tree Targeting (`SPECIFY_INIT_DIR`)

You can keep your specs in an out-of-tree folder or separate workspace while targeting the code repository. Set `SPECIFY_INIT_DIR`:

```bash
export SPECIFY_INIT_DIR="/path/to/my-shadow-specs"
specify session status
specify architecture generate --path /path/to/my-production-code
```

---

### Mode 3: Ephemeral Spec Branches & Traceability Export

1. Draft specs and plans on a local scratch branch or worktree:

   ```bash
   git checkout -b shadow/feature-user-auth
   /speckit-specify
   /speckit-plan
   /speckit-tasks
   ```

2. Implement code mutations on your primary production branch.
3. Run `/speckit-converge` to generate the final **Bidirectional Traceability Matrix** (FR-### $\leftrightarrow$ Code & Tests).
4. Paste the generated traceability table into your PR description as verification proof, leaving the upstream branch completely clean of scaffolding.
