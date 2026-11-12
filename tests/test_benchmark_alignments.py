"""Tests verifying benchmark alignment hardening against Tier 1 SDD criteria."""

from __future__ import annotations

from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
SPECIFY_CMD = TEMPLATES_DIR / "commands" / "specify.md"
CLARIFY_CMD = TEMPLATES_DIR / "commands" / "clarify.md"
PLAN_CMD = TEMPLATES_DIR / "commands" / "plan.md"
IMPLEMENT_CMD = TEMPLATES_DIR / "commands" / "implement.md"
TASKS_CMD = TEMPLATES_DIR / "commands" / "tasks.md"
CONVERGE_CMD = TEMPLATES_DIR / "commands" / "converge.md"
TASKS_TEMPLATE = TEMPLATES_DIR / "tasks-template.md"


def test_specify_socratic_gating_removes_premature_guessing() -> None:
    text = SPECIFY_CMD.read_text(encoding="utf-8")

    # Positive assertions: Socratic architectural gating
    assert "Socratic architectural interrogation" in text
    assert "Do NOT make silent or premature guesses on architectural forks" in text
    assert "Socratic Architectural Gating" in text

    # Negative assertions: No old guesswork directives or arbitrary limits
    assert "Make informed guesses based on context and industry standards" not in text
    assert "LIMIT: Maximum 3 [NEEDS CLARIFICATION] markers total" not in text
    assert "If more than 3 markers exist, keep only the 3 most critical" not in text


def test_clarify_removes_arbitrary_question_cap_on_architectural_forks() -> None:
    text = CLARIFY_CMD.read_text(encoding="utf-8")

    # Positive assertions: deep Socratic probing on architectural forks
    assert "Prioritize deep Socratic interrogation on architectural forks" in text
    assert (
        "Do NOT truncate or cut off questioning at an arbitrary count if high-impact architectural forks remain unsettled"
        in text
    )

    # Negative assertions: No hard 5-question session cutoff that cuts off unresolved forks
    assert "Maximum of 5 total questions across the whole session" not in text
    assert "- You reach 5 asked questions." not in text

    # Must preserve bounded planning deferral (regression test from #1717)
    assert "implementation method, tech-stack comparison, or task breakdown" in text


def test_implement_pre_mutation_state_safety_gate() -> None:
    text = IMPLEMENT_CMD.read_text(encoding="utf-8")

    # Pre-Mutation State Safety Gate
    assert "Pre-Mutation State Safety Gate" in text
    assert "Destructive File Operations" in text
    assert "Schema & Data Destruction" in text
    assert "Public API Contract Breaks" in text
    assert "Proceed with this mutation? (yes/no)" in text
    assert "Session Checkpoint" in text
    assert "session-checkpoint.json" in text


def test_tasks_dag_dependency_format() -> None:
    tasks_cmd_text = TASKS_CMD.read_text(encoding="utf-8")
    template_text = TASKS_TEMPLATE.read_text(encoding="utf-8")

    # tasks.md command template
    assert "blocked_by: [IDs]" in tasks_cmd_text
    assert "DAG Dependencies" in tasks_cmd_text

    # tasks-template.md
    assert "blocked_by: [IDs]" in template_text
    assert "(blocked_by: [T012, T013])" in template_text


def test_plan_enforces_spec_gating_gate() -> None:
    plan_text = PLAN_CMD.read_text(encoding="utf-8")

    # Must check spec gating before planning
    assert "Spec Gating Check" in plan_text
    assert "HALT IMMEDIATELY" in plan_text
    assert "Do NOT proceed to planning or generate `plan.md`" in plan_text
    assert "⛔ SPEC GATING ERROR: Unresolved Clarifications in spec.md" in plan_text
    assert "Run `/speckit-clarify` to answer them interactively" in plan_text


def test_clarify_socratic_grilling_and_adr_support() -> None:
    clarify_text = CLARIFY_CMD.read_text(encoding="utf-8")

    assert "adversarial staff engineer" in clarify_text
    assert "GLOSSARY.md" in clarify_text
    assert "docs/adr/ADR-" in clarify_text


def test_tasks_vertical_tracer_bullet_slicing() -> None:
    tasks_cmd_text = TASKS_CMD.read_text(encoding="utf-8")
    template_text = TASKS_TEMPLATE.read_text(encoding="utf-8")

    assert "Vertical Tracer-Bullet Slicing" in tasks_cmd_text
    assert "Atomic Blast Radius" in tasks_cmd_text
    assert "Tracer-Bullet Slices" in template_text


def test_implement_strict_tdd_rhythm() -> None:
    implement_text = IMPLEMENT_CMD.read_text(encoding="utf-8")

    assert "Strict Red-Green-Refactor Rhythm (TDD)" in implement_text
    assert "Red (Verify Failure)" in implement_text
    assert "Green (Minimal Pass)" in implement_text


def test_converge_dual_lens_audit() -> None:
    converge_text = CONVERGE_CMD.read_text(encoding="utf-8")

    assert "Dual-Lens Audit" in converge_text
    assert "Lens 1 (Spec & Requirement Traceability)" in converge_text
    assert "Lens 2 (Code Quality & Anti-Patterns)" in converge_text
    assert "Continuous Learning Retro" in converge_text


