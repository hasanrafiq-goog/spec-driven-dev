---
description: Identify underspecified areas in the current feature spec through Socratic grilling, asking targeted clarification questions and encoding answers back into the spec.
handoffs:
  - label: Build Technical Plan
    agent: speckit.plan
    prompt: Create a plan for the spec. I am building with...
scripts:
   sh: scripts/bash/check-prerequisites.sh --json --paths-only
   ps: scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly
   py: scripts/python/check_prerequisites.py --json --paths-only
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before clarification)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_clarify` key
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

Goal: Detect and reduce ambiguity or missing decision points in the active feature specification and record the clarifications directly in the spec file.

Note: This clarification workflow is expected to run (and be completed) BEFORE invoking `__SPECKIT_COMMAND_PLAN__`. If the user explicitly states they are skipping clarification (e.g., exploratory spike), you may proceed, but must warn that downstream rework risk increases.

Execution steps:

1. Run `{SCRIPT}` from repo root **once** (combined `--json --paths-only` mode / `-Json -PathsOnly`). Parse minimal JSON payload fields:
   - `FEATURE_DIR`
   - `FEATURE_SPEC`
   - (Optionally capture `IMPL_PLAN`, `TASKS` for future chained flows.)
   - If JSON parsing fails, abort and instruct user to re-run `__SPECKIT_COMMAND_SPECIFY__` or verify feature branch environment.
   - For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **IF EXISTS**: Load `/memory/constitution.md` for project principles and governance constraints.

3. Load the current spec file. Perform a structured Socratic ambiguity & coverage scan using this taxonomy. Act as an adversarial staff engineer probing architectural failure seams, edge cases, auth boundaries, race conditions, and ubiquitous domain concepts. For each category, mark status: Clear / Partial / Missing. Produce an internal coverage map used for prioritization (do not output raw map unless no questions will be asked).

   > ⚠️ **AUTONOMOUS DEEP-DIVE INVARIANT (CRITICAL)**:
   > Clarification is NOT limited to pre-existing `[NEEDS CLARIFICATION]` markers left by `__SPECKIT_COMMAND_SPECIFY__`. Even if the specification contains zero or only one `[NEEDS CLARIFICATION]` marker, `__SPECKIT_COMMAND_CLARIFY__` MUST conduct an independent, deep Socratic inquiry. It actively originates its own probing questions across the architectural taxonomy below, interrogating unstated assumptions, scale/concurrency limits, auth boundaries, failure modes, and trade-offs until genuine confidence reaches ~95%.

   Functional Scope & Behavior:
   - Core user goals & success criteria
   - Explicit out-of-scope declarations
   - User roles / personas differentiation

   Domain & Data Model:
   - Entities, attributes, relationships
   - Identity & uniqueness rules
   - Lifecycle/state transitions
   - Data volume / scale assumptions

   Interaction & UX Flow:
   - Critical user journeys / sequences
   - Error/empty/loading states
   - Accessibility or localization notes

   Non-Functional Quality Attributes:
   - Performance (latency, throughput targets)
   - Scalability (horizontal/vertical, limits)
   - Reliability & availability (uptime, recovery expectations)
   - Observability (logging, metrics, tracing signals)
   - Security & privacy (authN/Z, data protection, threat assumptions)
   - Compliance / regulatory constraints (if any)

   Integration & External Dependencies:
   - External services/APIs and failure modes
   - Data import/export formats
   - Protocol/versioning assumptions

   Edge Cases & Failure Handling:
   - Negative scenarios
   - Rate limiting / throttling
   - Conflict resolution (e.g., concurrent edits)

   Constraints & Tradeoffs:
   - Technical constraints (language, storage, hosting)
   - Explicit tradeoffs or rejected alternatives

   Terminology & Consistency:
   - Canonical glossary terms
   - Avoided synonyms / deprecated terms

   Completion Signals:
   - Acceptance criteria testability
   - Measurable Definition of Done style indicators

   Misc / Placeholders:
   - TODO markers / unresolved decisions
   - Ambiguous adjectives ("robust", "intuitive") lacking quantification

   For each category with Partial or Missing status, add a candidate question opportunity unless:
   - Clarification would not materially change implementation or validation strategy
   - The item is specifically about implementation method, tech-stack comparison, or task breakdown (note internally)

4. **Determine Resolution Mode**:
   Clarification supports 3 distinct ambiguity-resolution modes depending on the nature of the unknown:
   - **Mode A: Socratic Grilling (Human-in-the-Loop)**:
     - *Use when*: Human-decidable domain tradeoffs, user requirements, or business policies require clarification.
     - *Protocol*: Interactive sequential questioning loop (detailed below).
   - **Mode B: AFK Research Subagent (Deep Study)**:
     - *Use when*: External libraries, third-party APIs, legacy subsystems, or unfamiliar technologies require deep investigation.
     - *Protocol*: Dispatches background exploration task, analyzes documentation, and synthesizes findings into an Architectural Decision Record (`docs/adr/ADR-####-<topic>.md`).
   - **Mode C: Prototype Spike (Zero-Branch Scratchpad)**:
     - *Use when*: Empirical validation is needed (e.g., verifying an API payload, benchmark latency, or streaming capability).
     - *Protocol*: Executes in an isolated scratchpad directory (`specs/<feature>/spikes/<name>/` or temporary workspace) with **zero Git branch creation or switching**, preserving working tree safety. Findings and minimal snippets are synthesized into the spec and scratchpad files are cleaned up or preserved under `spikes/`.

5. **Dynamic Socratic Questioning Loop & Stance**:
   - **The Design Tree & Frontier Mental Model**:
     Do NOT treat clarification as a flat checklist of `[NEEDS CLARIFICATION]` markers from `__SPECKIT_COMMAND_SPECIFY__`. Map the system as a **Design Tree**: every architectural decision branches into the child decisions that hang off it.
     Work the tree in sequential probes along the **Frontier**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask *now* without guessing at answers you haven't heard yet.
     Settling an initial decision (e.g. backend transport or basic CRUD) does NOT end clarification—it pushes the frontier outward and unblocks downstream child decisions:
     - *Client & Rendering Environment*: Offline/air-gapped resilience, corporate VPN/firewall CDN blocking, local asset bundling.
     - *Data Contract & State Lifecycle*: Multi-run reset, idempotency, schema evolution, versioning.
     - *Concurrency & Error Boundaries*: Catastrophic 6-month pre-mortem failure seams.
   - **Separation of Facts vs. Decisions (Autonomous Fact Hunting)**:
     Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, codebase AST, existing dependencies, configuration), use your tools to look it up autonomously; NEVER ask the user for anything you could inspect yourself. The _decisions_ (trade-offs, user requirements, business boundaries) are the user's: formulate each decision as an opinionated probe and wait.
   - **Hypothesis-First Read & Dynamic Confidence Scoring**:
     Before asking any questions, the agent MUST assess its internal mental model and output its initial hypothesis and confidence:
     ```text
     HYPOTHESIS: <One sentence capturing the underlying user need beneath the conventional request>
     CONFIDENCE: ~X% — missing: <exact unresolved blind spots: who it's for, binding constraint, or failure mode>
     ```
     Confidence is scored on a 0–100% scale and must be dynamically updated as questions are answered.
   - **The Anti-Inflation Invariant & 70% Specify Ceiling**:
     Resolving pre-existing `[NEEDS CLARIFICATION]` markers from `__SPECKIT_COMMAND_SPECIFY__` only clears known surface unknowns. **Confidence is strictly capped at ≤ 70% if only specify markers have been answered.** The agent is STRICTLY FORBIDDEN from declaring ≥ 90% confidence until it has explored child decisions on the frontier and resolved at least one independent probe on operational, network/resilience, or data-contract failure seams unmentioned in `specify.md`.
   - **Eradication of Question Quotas**:
     Prioritize deep Socratic interrogation on architectural forks, data contracts, and security boundaries. Do NOT truncate or cut off questioning at an arbitrary count if high-impact architectural forks remain unsettled (no 3-question limits, no 5-question round caps, no question-quota deferrals). Questioning runs strictly sequentially, one probe at a time, until confidence reaches ~95% or the user explicitly halts (`done`, `proceed`).
   - **Autonomous Question Origination Beyond Specify**:
     Questions MUST NOT be confined to markers discovered in the specify phase. The agent independently audits the taxonomy, uncovers latent failure seams, and originates its own grilling probes across all Partial or Missing areas, regardless of how few markers existed in `spec.md`.
   - **Guess-Attached Questioning Protocol**:
     Every clarification probe presented to the user MUST take an active technical stance and strictly adhere to:
     ```text
     **Question:** <Full interrogative ending with a question mark>?
     **Why it matters:** <One plain-language sentence explaining the concrete stake for acceptance or shipping>
     **My Guess:** <The agent's specific prediction of the answer, backed by explicit technical reasoning>
     ```
   - **Bulleted Options for Discrete Architectural Forks (Table Ban)**:
     When mutually exclusive architectural choices exist (e.g., Option A vs Option B), list them as concise bullet points directly under the guess:
     ```text
     - Option A: <Description of alternative A>
     - Option B: <Description of alternative B>
     ```
     Markdown survey tables (e.g., table grids with pipes and option columns) are strictly FORBIDDEN in the interactive clarification dialogue to eliminate terminal line-wrapping corruption on narrow screens.
   - **The "Want vs. Should Want" Anti-Rationalization Filter**:
     Actively listen for buzzwords or textbook rationalization ("enterprise-grade", "industry standard", "clean architecture", "we should probably..."). When detected, interrupt the convention and ask:
     > *"If you didn't have to justify this to anyone, what would you actually want to happen here?"*
   - **Adversarial Pre-Mortem Failure Probing**:
     Prior to concluding clarification on any non-trivial feature or breaking change, conduct an adversarial pre-mortem probe with an attached failure prediction:
     ```text
     **Question:** Imagine this feature ships to production and causes an outage, regression, or rewrite in 6 months. What was the hidden failure seam that caused it?
     **Why it matters:** Surfacing latent failure seams now prevents production incidents and costly refactors.
     **My Guess:** The biggest catastrophic breakdown risk is <agent's specific hypothesized failure seam>.
     ```
   - **The ~95% Confidence Stop Heuristic (Empty Frontier)**:
     Questioning does NOT stop based on an arbitrary counter. Questioning stops when:
     1. (The **frontier is empty**: every branch of the design tree has been visited, and nothing is left silently assumed across the core architectural taxonomy, reaching ~95% confidence AND all high-impact architectural forks have been resolved and confirmed), OR
     2. The user explicitly requests early exit (`done`, `proceed`, `skip`, `stop`).
   - **Handling User Feedback & Abdication**:
     - **User Corrects a Guess**: If the user refutes or corrects the agent's guess, immediately adopt the correction, update the `HYPOTHESIS:` in the next turn without defensive rationalization, and probe any downstream implications.
     - **User Abdication ("Whatever you think")**: If the user responds with "whatever you think", "you decide", or similar on a critical architectural fork, do NOT blindly proceed or accept abdication. Respectfully decline the abdication, succinctly restate the best guess along with the concrete operational, security, or architectural risks of that choice, and request an explicit decision or endorsement.
   - **Confirmed Intent Deliverable with Explicit Out-of-Scope**:
     When confidence reaches ~95%, present the confirmed intent deliverable:
     ```text
     Here is the confirmed intent:
     - Outcome:      <one line — the actual tangible result>
     - User:         <one line — who specifically benefits>
     - Why now:      <one line — what triggered this change>
     - Success:      <one line — the measurable checkable proof of success>
     - Constraint:   <one line — the binding limit or non-negotiable invariant>
     - Out of scope: <one line — what we are EXPLICITLY NOT doing>

     Confirm (yes / no / refine)?
     ```
     The agent MUST receive an affirmative confirmation before declaring clarification complete.

6. Integration after EACH accepted answer (incremental update approach):
    - Maintain in-memory representation of the spec (loaded once at start) plus the raw file contents.
    - For the first integrated answer in this session:
       - Ensure a `## Clarifications` section exists (create it just after the highest-level contextual/overview section per the spec template if missing).
       - Under it, create (if not present) a `### Session YYYY-MM-DD` subheading for today.
    - Append a bullet line immediately after acceptance: `- Q: <question> → A: <final answer>`.
    - When clarification concludes and Confirmed Intent is affirmatively confirmed by the user:
       - Ensure a `### Confirmed Intent & Non-Goals` block is written or updated under `## Clarifications` with the final confirmed 6 lines (Outcome, User, Why now, Success, Constraint, Out of scope).
    - Then immediately apply the clarification to the most appropriate section(s):
       - Functional ambiguity → Update or add a bullet in Functional Requirements.
       - User interaction / actor distinction → Update User Stories or Actors subsection (if present) with clarified role, constraint, or scenario.
       - Data shape / entities → Update Data Model (add fields, types, relationships) preserving ordering; note added constraints succinctly.
       - Non-functional constraint → Add/modify measurable criteria in Success Criteria > Measurable Outcomes (convert vague adjective to metric or explicit target).
       - Edge case / negative flow → Add a new bullet under Edge Cases / Error Handling (or create such subsection if template provides placeholder for it).
       - Terminology conflict → Normalize term across spec; retain original only if necessary by adding `(formerly referred to as "X")` once.
    - If the clarification invalidates an earlier ambiguous statement, replace that statement instead of duplicating; leave no obsolete contradictory text.
    - **Ubiquitous Language & Glossary**: If a domain term or actor definition is clarified or standardized, record or append it to `.specify/memory/GLOSSARY.md` (create file if missing) mapping term to its definition.
    - **Architectural Decision Record (ADR)**: If the clarification resolves a major architectural fork or permanent design tradeoff, write a concise ADR in `docs/adr/ADR-####-<topic>.md` (create directory if missing) documenting Status, Context, Decision, and Consequences, and cross-reference the ADR in `spec.md`.
    - Save the spec file AFTER each integration to minimize risk of context loss (atomic overwrite).
    - Preserve formatting: do not reorder unrelated sections; keep heading hierarchy intact.
    - Keep each inserted clarification minimal and testable (avoid narrative drift).

7. Validation (performed after EACH write plus final pass):
   - Clarifications session contains exactly one bullet per accepted answer (no duplicates).
   - Questions in this interactive round are validated and resolved.
   - Updated sections contain no lingering vague placeholders the new answer was meant to resolve.
   - No contradictory earlier statement remains (scan for now-invalid alternative choices removed).
   - Markdown structure valid; only allowed new headings: `## Clarifications`, `### Session YYYY-MM-DD`, `### Confirmed Intent & Non-Goals`.
   - Terminology consistency: same canonical term used across all updated sections.

8. Write the updated spec back to `FEATURE_SPEC`.

9. **Re-validate Spec Quality Checklist** (if it exists):
   - Check if `FEATURE_DIR/checklists/requirements.md` exists.
   - If it does NOT exist, skip this step silently.
   - If it exists:
     1. Read the checklist file.
     2. Identify all GitHub task-list checkbox lines — lines matching `- [ ]`, `- [x]`, or `- [X]` (case-insensitive, tolerant of leading whitespace for nested items) outside of code fences. Ignore all other content (headings, notes, non-checkbox bullets, metadata).
     3. For each checkbox line, record its current marker state (checked or unchecked) and item text into a before-snapshot list.
     4. Re-evaluate each checkbox item against the **updated** spec (the version just saved in step 7).
     5. For each checkbox item, update only if the checked/unchecked state actually changes:
        - If the item now passes and was unchecked: change `[ ]` to `[x]`.
        - If the item now fails and was checked: change `[x]`/`[X]` to `[ ]`.
        - If the state is unchanged: leave the marker as-is (preserve existing case to avoid cosmetic diffs).
     6. Save the updated checklist file. **Only toggle the `[ ]`/`[x]` marker portion of checkbox lines whose state changed.** All other file content — headings, metadata, notes, line ordering, whitespace — must remain unchanged to avoid noisy diffs.
     7. Compare the before-snapshot with the current state to compute three lists for the Completion Report:
        - **Newly passing**: items that changed from unchecked to checked.
        - **Regressions**: items that changed from checked to unchecked.
        - **Still unchecked**: items that remain unchecked.
     8. Record the before/after pass counts as checked/total checkbox items (e.g., "12/16 → 15/16 items passing").

Behavior rules:

- If no meaningful ambiguities found (or all potential questions would be low-impact), respond: "No critical ambiguities detected worth formal clarification." and suggest proceeding.
- If spec file missing, instruct user to run `__SPECKIT_COMMAND_SPECIFY__` first (do not create a new spec here).
- Question sequentially one probe at a time without arbitrary quotas or batch caps, continuing until confidence reaches ~95% or all critical architectural forks are settled (clarification retries for a single question do not count as new questions).
- Avoid speculative tech stack questions unless the absence blocks functional clarity.
- Respect user early termination signals ("stop", "done", "proceed").
- If no questions asked due to full coverage, output a compact coverage summary (all categories Clear) then suggest advancing.
- If any high-impact categories remain deferred or unresolved, explicitly flag them under Deferred with rationale.

Context for prioritization: {ARGS}

## Mandatory Post-Execution Hooks

**You MUST complete this section before reporting completion to the user.**

Check if `.specify/extensions.yml` exists in the project root.
- If it does not exist, or no hooks are registered under `hooks.after_clarify`, skip to the Completion Report.
- If it exists, read it and look for entries under the `hooks.after_clarify` key.
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

### Central SDLC Board Synchronization

You **MUST** synchronize with the central project tracker `.specify/BOARD.md`:
- If `.specify/BOARD.md` exists:
  - **Human-in-the-Loop Blocker Assignment (@human)**: If any critical architectural decisions, security boundaries, domain trade-offs, or external requirements cannot be resolved autonomously or require human sign-off, add or update a ticket under `## 🛑 Blocked & Awaiting Human Input (@human)`:
    ```markdown
    - [ ] **[{FEATURE_ID}-DECISION-{NUM}]** {DECISION_TITLE}
      - **Type**: `Decision`
      - **Stage**: `Clarify`
      - **Status**: `BLOCKED`
      - **Assignee**: `@human`
      - **Feature Path**: `{FEATURE_DIR}`
      - **Tagged Artifacts**: `[{FEATURE_SPEC}#L{LINE}]({FEATURE_SPEC}#L{LINE})`, `[ADR-{NUM}](docs/adr/ADR-{NUM}.md)`
      - **Blocked By**: `None`
      - **Context & Human Action Needed**: {Specific question, architectural fork, or trade-off requiring human review}.
    ```
  - **When all clarifications are settled**: Move or update the feature entry to `## 🟡 Ready for Work`:
    ```markdown
    - [ ] **[{FEATURE_ID}]** {FEATURE_TITLE}
      - **Type**: `Feature`
      - **Stage**: `Plan`
      - **Status**: `READY`
      - **Assignee**: `@agent-plan`
      - **Feature Path**: `{FEATURE_DIR}`
      - **Tagged Artifacts**: `[{FEATURE_SPEC}]({FEATURE_SPEC})`, `[.specify/memory/GLOSSARY.md](.specify/memory/GLOSSARY.md)`
      - **Blocked By**: `None`
      - **Action / Input Needed**: Ready for `__SPECKIT_COMMAND_PLAN__`.
    ```
  - **Fog of War Resolution**: If this clarification resolved an item residing in `## 🌫️ Fog of War (Not Yet Specified)`, update its status to `RESOLVED` and promote the unblocked feature or task to `## 🟡 Ready for Work` (or `Backlog`) with `Stage: Plan`.

## Completion Report

Report completion (after questioning loop ends or early termination):
- Number of questions asked & answered.
- Path to updated spec.
- Sections touched (list names).
- Spec quality checklist status (if `FEATURE_DIR/checklists/requirements.md` was re-validated): show before/after pass counts (e.g., "Spec Quality Checklist: 12/16 → 15/16 items passing") and list any items that changed state — both newly checked (unchecked → checked) and any regressions (checked → unchecked). If any items remain unchecked, list them as areas needing attention.
- Coverage summary table listing each taxonomy category with Status: Resolved (was Partial/Missing and addressed), Deferred (remaining item is specifically implementation method, tech-stack comparison, or task breakdown per issue #1717; never defer acceptance criteria or edge cases due to question count), Clear (already sufficient), Outstanding (still Partial/Missing but low impact).
- If any Outstanding or Deferred remain, recommend whether to proceed to `__SPECKIT_COMMAND_PLAN__` or run `__SPECKIT_COMMAND_CLARIFY__` again later post-plan.
- Suggested next command.

## Done When

- [ ] Spec ambiguities identified and clarifications integrated into spec file
- [ ] Central SDLC board updated in `.specify/BOARD.md` (unresolved forks routed to `@human`, resolved features moved to `Ready for Work`)
- [ ] Spec quality checklist re-validated against updated spec (if `FEATURE_DIR/checklists/requirements.md` exists)
- [ ] Extension hooks dispatched or skipped according to the rules in Mandatory Post-Execution Hooks above
- [ ] Completion reported to user with questions answered, sections touched, checklist status, and coverage summary
