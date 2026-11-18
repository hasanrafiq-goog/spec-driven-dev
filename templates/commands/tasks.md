---
description: Generate an actionable, dependency-ordered tasks.md for the feature based on available design artifacts.
handoffs:
  - label: Analyze For Consistency
    agent: speckit.analyze
    prompt: Run a project analysis for consistency
    send: true
  - label: Implement Project
    agent: speckit.implement
    prompt: Start the implementation in phases
    send: true
scripts:
  sh: scripts/bash/setup-tasks.sh --json
  ps: scripts/powershell/setup-tasks.ps1 -Json
  py: scripts/python/setup_tasks.py --json
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before tasks generation)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_tasks` key
- If the YAML cannot be parsed or is invalid, do not skip silently: tell the user that `.specify/extensions.yml` could not be read (include the parser error) and that no hooks were checked, including any mandatory (`optional: false`) hooks registered there, then halt immediately with a fatal error.
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}

    Wait for the result of the hook command before proceeding to the Outline.
    ```
    After emitting the block above you MUST actually invoke the hook and wait for it to finish before continuing. Run it the same way you would run the command yourself in this agent/session (the invocation may differ from the literal `{command}` id shown above, e.g. a skills-mode agent runs it as `/skill:speckit-...` or `$speckit-...`). Emitting the block alone does not run the hook.
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently

## Outline

1. **Setup**: Run `{SCRIPT}` from repo root and parse FEATURE_DIR, TASKS_TEMPLATE_CONTENT, TASKS_TEMPLATE, and AVAILABLE_DOCS list. `FEATURE_DIR` and `TASKS_TEMPLATE` must be absolute paths when provided. `AVAILABLE_DOCS` is a list of document names/relative paths available under `FEATURE_DIR` (for example `research.md` or `contracts/`). For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Load design documents & Verify Gating**: Read from FEATURE_DIR:
   - **Required**: plan.md (tech stack, libraries, structure), spec.md (user stories with priorities)
   - **Optional**: data-model.md (entities), contracts/ (interface contracts), research.md (decisions), quickstart.md (test scenarios)
   - **IF EXISTS**: Load `/memory/constitution.md` for project principles and governance constraints
   - **Spec Gating Check**: Verify that `spec.md` has no unresolved `[NEEDS CLARIFICATION]` markers or pending questions. If unresolved markers exist, HALT and instruct the user to run `/speckit-clarify` first.
   - **Board Blocker Check**: Check `.specify/BOARD.md` (if it exists). If any ticket for this feature is listed under `## 🛑 Blocked & Awaiting Human Input (@human)` with status `BLOCKED`, HALT and inform the user that human blockers must be resolved before slicing tasks.
   - Note: Not all projects have all documents. Generate tasks based on what's available.

3. **Execute task generation workflow**:
   - Load plan.md and extract tech stack, libraries, project structure
   - Load spec.md and extract user stories with their priorities (P1, P2, P3, etc.)
   - If data-model.md exists: Extract entities and map to user stories
   - If contracts/ exists: Map interface contracts to user stories
   - If research.md exists: Extract decisions for setup tasks
   - Generate tasks organized by user story (see Task Generation Rules below)
   - Generate dependency graph showing user story completion order
   - Create parallel execution examples per user story
   - Validate task completeness (each user story has all needed tasks, independently testable)

4. **Generate tasks.md**: Use TASKS_TEMPLATE_CONTENT (from the JSON output above) as the structure. For compatibility with older setup scripts that omit TASKS_TEMPLATE_CONTENT, read TASKS_TEMPLATE instead. Fill with:
   - Correct feature name from plan.md
   - Phase 1: Setup tasks (project initialization)
   - Phase 2: Foundational & **Vertical Tracer Bullet** (Task 1/MVP MUST deliver a minimal working end-to-end walking skeleton with a passing integration test before horizontal breadth)
   - Phase 3+: One phase per user story (in priority order from spec.md)
   - Each phase includes: story goal, independent test criteria, mandatory failing test tasks (TDD with **Anti-Mocking Dogma**: never mock internal collaborators; mocks permitted ONLY at external I/O boundaries), implementation tasks
   - Final Phase: Polish & cross-cutting concerns
   - All tasks must follow the strict checklist format (see Task Generation Rules below)
   - Clear file paths for each task
   - Dependencies section showing story completion order
   - Parallel execution examples per story
   - Implementation strategy section (MVP first, incremental delivery)

5. **Central SDLC Board Synchronization**:
   - If `.specify/BOARD.md` exists (preserving all existing/past feature cards — **No-Overwrite / No-Truncation Invariant**):
     - Under `## 🟡 Ready for Work`, list the generated tasks:
       - Record each task with its ID, title, status (`READY` for root/unblocked tasks, `BLOCKED` for dependent tasks), assignee (`@agent-implement`), tagged target file paths, and `Blocked By` dependencies (derived from the DAG).
       - Ensure the parent feature ticket is marked `Stage: Implement`, `Status: READY`.
     - Run `specify board sync` if `.specify/init-options.json` configures a remote `board_provider`.

6. **Local-First Issue Tracker Synchronization (Optional Background Hook)**:
   - **Local Default**: Issue tracking defaults to `tracker: local` (100% offline, zero network requests, zero required API keys).
   - **Remote Synchronization**: When an external issue tracker is enabled (`tracker: github` / `linear` / `jira`), background hooks silently create child issues under the feature epic and tag each task with an idempotent metadata comment:
     `- [ ] T001 Description <!-- tracker:github#123 -->`
   - Re-running tasks MUST preserve existing `<!-- tracker:... -->` tags and avoid creating duplicate tickets.
   - **Failure Handling**: If a remote sync call fails during interactive execution, prompt the user with `[R]etry / [C]ontinue local / [D]isable`. In non-interactive/CI environments, fall back automatically to local-only with a logged warning.

## Mandatory Post-Execution Hooks

**You MUST complete this section before reporting completion to the user.**

Check if `.specify/extensions.yml` exists in the project root.
- If it does not exist, or no hooks are registered under `hooks.after_tasks`, skip to the Completion Report.
- If it exists, read it and look for entries under the `hooks.after_tasks` key.
- If the YAML cannot be parsed or is invalid, do not skip silently: tell the user that `.specify/extensions.yml` could not be read (include the parser error) and that no hooks were checked, including any mandatory (`optional: false`) hooks registered there, then halt immediately with a fatal error.
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
- For each executable hook, output the following based on its `optional` flag:
  - **Mandatory hook** (`optional: false`) — **You MUST emit `EXECUTE_COMMAND:` for each mandatory hook**:
    ```
    ## Extension Hooks

    **Automatic Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    ```
    After emitting the block above you MUST actually invoke the hook and wait for it to finish before continuing. Run it the same way you would run the command yourself in this agent/session (the invocation may differ from the literal `{command}` id shown above, e.g. a skills-mode agent runs it as `/skill:speckit-...` or `$speckit-...`). Emitting the block alone does not run the hook.
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```

## Completion Report

Output path to generated tasks.md and summary:
- Total task count
- Task count per user story
- Parallel opportunities identified
- Independent test criteria for each story
- Suggested MVP scope (typically just User Story 1)
- Format validation: Confirm ALL tasks follow the checklist format (checkbox, ID, labels, file paths)

Context for task generation: {ARGS}

The tasks.md should be immediately executable - each task must be specific enough that an LLM can complete it without additional context.

## Task Generation Rules

**CRITICAL**: Tasks MUST be organized by user story to enable independent implementation and testing.

**Mandatory TDD (Red-Green-Refactor)**: Every user story phase MUST include automated test tasks scheduled before implementation. Tests must be written and observed to fail before implementation code is written.

### Checklist Format (REQUIRED)

Every task MUST strictly follow this format:

```text
- [ ] [TaskID] [P?] [Story?] Description with file path (blocked_by: [IDs])
```

**Format Components**:

1. **Checkbox**: ALWAYS start with `- [ ]` (markdown checkbox)
2. **Task ID**: Sequential number (T001, T002, T003...) in execution order
3. **[P] marker**: Include ONLY if task is parallelizable (different files, no dependencies on incomplete tasks)
4. **[Story] label**: REQUIRED for user story phase tasks only
   - Format: [US1], [US2], [US3], etc. (maps to user stories from spec.md)
   - Setup phase: NO story label
   - Foundational phase: NO story label
   - User Story phases: MUST have story label
   - Polish phase: NO story label
5. **Description**: Clear action with exact file path
6. **DAG Dependencies**: Append `(blocked_by: [T###, ...])` when a task depends on outputs from prior tasks. Enables parallel multi-worktree tracer-bullet execution.

**Examples**:

- ✅ CORRECT: `- [ ] T001 Create project structure per implementation plan`
- ✅ CORRECT: `- [ ] T005 [P] Implement authentication middleware in src/middleware/auth.py`
- ✅ CORRECT: `- [ ] T010 [P] [US1] Write failing contract test in tests/contract/test_user.py`
- ✅ CORRECT: `- [ ] T012 [P] [US1] Create User model in src/models/user.py (blocked_by: [T010])`
- ✅ CORRECT: `- [ ] T014 [US1] Implement UserService in src/services/user_service.py (blocked_by: [T012])`
- ❌ WRONG: `- [ ] Create User model` (missing ID and Story label)
- ❌ WRONG: `T001 [US1] Create model` (missing checkbox)
- ❌ WRONG: `- [ ] [US1] Create User model` (missing Task ID)
- ❌ WRONG: `- [ ] T001 [US1] Create model` (missing file path)

### Task Organization

1. **Vertical Tracer-Bullet Slicing (CRITICAL)**:
   - **Vertical over Horizontal**: Do NOT group tasks by horizontal architectural layers (e.g., all database models in phase 1, all services in phase 2). Slice vertically per user story so each phase delivers an end-to-end, testable increment.
   - **Atomic Blast Radius**: Each individual task must touch $\le$ 3 files. If a task requires modifying more than 3 files, break it into smaller vertical subtasks.
   - **Expand–Contract Pattern for Wide Refactors**: Any task modifying shared public interfaces MUST follow Expand–Contract (Phase 1: Expand new interface $\rightarrow$ Phase 2: Migrate call sites incrementally $\le 3$ files $\rightarrow$ Phase 3: Contract deprecated interface) to ensure intermediate tests never break.
   - **DAG Blocked-By Dependencies**: For tasks that depend on outputs from earlier tasks, append `(blocked_by: [T###])`. Tasks without dependencies should be tagged `[P]` for parallel dispatch.

2. **From User Stories (spec.md)** - PRIMARY ORGANIZATION:
   - Each user story (P1, P2, P3...) gets its own phase
   - Map all related components to their story:
     - Automated tests specific to that story (failing test tasks scheduled first)
     - Models needed for that story
     - Services needed for that story
     - Interfaces/UI needed for that story
   - Mark story dependencies (most stories should be independent)

3. **From Contracts**:
   - Map each interface contract → to the user story it serves
   - Each interface contract → contract test task [P] before implementation in that story's phase

4. **From Data Model**:
   - Map each entity to the user story(ies) that need it
   - If entity serves multiple stories: Put in earliest story or Setup phase
   - Relationships → service layer tasks in appropriate story phase
   - For each field with constraints in data-model.md (max length, nullable/required, enum values, validation rules), quote the constraint verbatim in the task description so it is not left to implementation-time discretion

5. **From Setup/Infrastructure**:
   - Shared infrastructure → Setup phase (Phase 1)
   - Foundational/blocking tasks → Foundational phase (Phase 2)
   - Story-specific setup → within that story's phase

### Phase Structure

- **Phase 1**: Setup (project initialization)
- **Phase 2**: Foundational (blocking prerequisites - MUST complete before user stories)
- **Phase 3+**: User Stories in priority order (P1, P2, P3...)
  - Within each story: Mandatory Failing Tests (TDD) → Models → Services → Endpoints → Integration
  - Each phase should be a complete, independently testable increment
- **Final Phase**: Polish & Cross-Cutting Concerns

## Done When

- [ ] tasks.md generated with all phases, task IDs, and file paths
- [ ] Central SDLC board in `.specify/BOARD.md` synchronized with generated task DAG and dependencies
- [ ] Extension hooks dispatched or skipped according to the rules in Mandatory Post-Execution Hooks above
- [ ] Completion reported to user with task count, story breakdown, and MVP scope
