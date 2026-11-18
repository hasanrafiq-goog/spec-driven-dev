"""Parity tests verifying all 13 architectural upgrades in core templates with zero new external skills."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_core_templates_encode_architectural_evolution_invariants() -> None:
    spec_tpl = (REPO_ROOT / "templates" / "spec-template.md").read_text(encoding="utf-8")
    plan_tpl = (REPO_ROOT / "templates" / "plan-template.md").read_text(encoding="utf-8")
    tasks_tpl = (REPO_ROOT / "templates" / "tasks-template.md").read_text(encoding="utf-8")

    assert "_Avoid_" in spec_tpl
    assert "Visual & Interaction Prototype Sign-off" in spec_tpl
    assert "Design It Twice" in plan_tpl
    assert "3-Condition ADR Gate" in plan_tpl
    assert "Deletion Test" in plan_tpl
    assert "Anti-Mocking Dogma" in tasks_tpl
    assert "Test Change Rule" in tasks_tpl
    assert "Vertical Tracer Bullets" in tasks_tpl


def test_command_templates_wire_skills_without_creating_external_skills() -> None:
    cmds_dir = REPO_ROOT / "templates" / "commands"
    specify_md = (cmds_dir / "specify.md").read_text(encoding="utf-8")
    clarify_md = (cmds_dir / "clarify.md").read_text(encoding="utf-8")
    plan_md = (cmds_dir / "plan.md").read_text(encoding="utf-8")
    tasks_md = (cmds_dir / "tasks.md").read_text(encoding="utf-8")
    implement_md = (cmds_dir / "implement.md").read_text(encoding="utf-8")
    converge_md = (cmds_dir / "converge.md").read_text(encoding="utf-8")

    assert "No-Overwrite / No-Truncation Invariant" in specify_md
    assert "First-Run Board Backend Selection" in specify_md
    assert "GLOSSARY-MAP.md" in specify_md
    assert "QUESTIONNAIRE.md" in clarify_md
    assert ".specify/prototypes/" in clarify_md
    assert "specify architecture generate --visual" in plan_md
    assert "3-Condition ADR Gate" in plan_md
    assert "Anti-Mocking Dogma" in tasks_md
    assert "Vertical Tracer Bullet" in tasks_md
    assert "Test Change Rule" in implement_md
    assert "git merge-base" in converge_md
    assert ".specify/memory/learnings.md" in converge_md
    assert "specify board sync" in converge_md

    # Ensure no top-level standalone skills/ directory was introduced
    assert not (REPO_ROOT / "skills").exists()
