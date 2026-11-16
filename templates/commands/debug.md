---
description: "Diagnose root causes with minimal reproductions and evolve living specs."
handoffs:
  - label: Clarify Fix Specification
    agent: speckit.clarify
    prompt: Clarify fix specification requirements
    send: true
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

**Check for extension hooks (before debugging)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_debug` key
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
    After emitting the block above you MUST actually invoke the hook and wait for it to finish before continuing. Emitting the block alone does not run the hook.
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently

## Outline

Goal: Systematically diagnose unexpected defects and root causes without "shotgun debugging", producing a verified Diagnostic Bundle and routing the defect through the appropriate lifecycle ramp to permanently prevent spec drift.

Execution Steps:

1. Run `{SCRIPT}` from repo root **once** (combined `--json --paths-only` mode / `-Json -PathsOnly`) to verify active feature environment and prerequisites. Parse minimal JSON payload fields: `FEATURE_DIR`, `FEATURE_SPEC`.

### Phase 1: Understand
1. Ingest symptoms from user input, error logs, and stack traces.
2. Locate the failing subsystem using the architecture index (`.specify/memory/architecture/`).
3. Construct a minimal, deterministic reproduction script or isolated test case (`tests/reproduce_*.py` or scratchpad test).
4. Run the reproduction test and observe it **fail deterministically**.

### Phase 2: Hypothesize
1. Formulate 2–3 mutually exclusive, falsifiable hypotheses explaining why the failure occurs.
2. For each hypothesis, state an initial confidence score (0–100%), the missing evidence, and the exact observation probe that will confirm or disprove it without premature guesswork.

### Phase 3: Isolate
> ⚠️ **ANTI-SHOTGUN DEBUGGING RULE (CRITICAL)**:
> **DO NOT write fix code during the isolation phase.** Only write assertions and observation probes. If you write fix code before proving a hypothesis, you are guessing.

1. Inject temporary assertions or probes to test each hypothesis in order.
2. Confirm which hypothesis is **PROVEN** and which are **DISPROVEN**.
3. Identify the exact root-cause failure seam (e.g., invalidated business assumption, missing boundary validation, unhandled asynchronous state).

### Phase 4: Output Diagnostic Bundle
Generate the incident artifact at `specs/incidents/BUG-{NNN}.md`:

```markdown
# Incident Diagnosis: BUG-{NNN}

**Reported**: {TIMESTAMP}
**Symptom**: {OBSERVED_ERROR}
**Reproduction Test**: `{TEST_FILE}::{TEST_FUNCTION}`

## Root Cause Analysis
{DETAILED_FAILURE_SEAM_ANALYSIS}

## Hypotheses Matrix
| Hypothesis | Initial Confidence | Evidence | Result |
| :--- | :--- | :--- | :--- |
| H1: ... | ~30% | ... | DISPROVEN |
| H2: ... | ~70% | ... | PROVEN |

## Classification & Ramp Recommendation
- **Classification**: `SPECIFICATION_GAP` | `IMPLEMENTATION_DEFECT`
- **Action**: `RAMP_B_SPEC_EVOLUTION` | `RAMP_A_FAST_PATCH`
```

---

## The Two Exit Ramps

### Primary Flow: Ramp B (Customer Journey Evolution)
*Recommended for all non-trivial defects, unhandled states, or contract gaps.*

1. **Seed Living Spec**: Automatically create `specs/FIX-{NNN}-{slug}/spec.md`:
   - **User Story**: Derived directly from the failure scenario ("As a [User], when [Failing Scenario], I expect [Graceful Outcome]").
   - **Acceptance Criteria**: Pre-populated with the exact Given/When/Then assertions from the reproduction test.
   - **Edge Cases**: Pre-populated from evaluated hypotheses.
2. **Register on Board**: Add `[FIX-{NNN}]` to `.specify/BOARD.md` under `## 📋 Backlog & Clarification Needed`.
3. **Lifecycle Handoff**: Direct the user to `__SPECKIT_COMMAND_CLARIFY__` $\rightarrow$ `__SPECKIT_COMMAND_PLAN__` $\rightarrow$ `__SPECKIT_COMMAND_TASKS__` $\rightarrow$ `__SPECKIT_COMMAND_IMPLEMENT__` $\rightarrow$ `__SPECKIT_COMMAND_CONVERGE__`. This guarantees zero spec drift and treats the defect as a first-class product increment.

### Escape Valve: Ramp A (Fast Patch)
*Reserved strictly for localized regressions or syntax typos where the existing `spec.md` is already 100% accurate and unambiguous.*

1. Move minimal reproduction script into a permanent regression test in `tests/`.
2. Apply minimal atomic fix ($\le 3$ files).
3. Run test runner to confirm regression test passes and no existing tests break.
4. Record resolution in `specs/incidents/BUG-{NNN}.md`.

---

## Mandatory Post-Execution Hooks

**You MUST complete this section before reporting completion to the user.**

Check if `.specify/extensions.yml` exists in the project root.
- If it does not exist, or no hooks are registered under `hooks.after_debug`, skip to the Completion Report.
- If it exists, read it and look for entries under the `hooks.after_debug` key.
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
    After emitting the block above you MUST actually invoke the hook and wait for it to finish before continuing. Emitting the block alone does not run the hook.
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```

## Central SDLC Board Synchronization

You **MUST** synchronize with `.specify/BOARD.md`:
- If Ramp B is selected:
  - Add the new fix feature under `## 📋 Backlog & Clarification Needed` (`Stage: Clarify`, `Status: READY`).
- If Ramp A is selected:
  - Update `BOARD.md` marking the incident resolved under `## ✅ Done & Converged`.

## Completion Report

Report completion to user:
- Path to Diagnostic Bundle (`specs/incidents/BUG-###.md`).
- Summary of verified root cause.
- Selected exit ramp (Ramp B spec evolution vs. Ramp A fast patch).
- Next recommended command.
