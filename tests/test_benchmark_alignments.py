"""Tests verifying benchmark alignment hardening against Tier 1 SDD criteria."""

from __future__ import annotations

from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
SPECIFY_CMD = TEMPLATES_DIR / "commands" / "specify.md"
CLARIFY_CMD = TEMPLATES_DIR / "commands" / "clarify.md"
IMPLEMENT_CMD = TEMPLATES_DIR / "commands" / "implement.md"
TASKS_CMD = TEMPLATES_DIR / "commands" / "tasks.md"
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
