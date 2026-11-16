"""Tests for Divergent Interface Exploration ("Design It Twice") in /speckit-plan."""

from __future__ import annotations

from pathlib import Path
import pytest


def test_plan_template_mandates_design_it_twice_phase_1(repo_templates_dir: Path):
    plan_md = repo_templates_dir / "plan.md"
    content = plan_md.read_text(encoding="utf-8")
    assert "Design It Twice" in content, (
        "plan.md MUST explicitly mandate the 'Design It Twice' divergent design exploration in Phase 1"
    )


def test_plan_template_defines_three_competing_designs(repo_templates_dir: Path):
    plan_md = repo_templates_dir / "plan.md"
    content = plan_md.read_text(encoding="utf-8")
    assert "Minimal Interface" in content, "plan.md must evaluate Minimal Interface"
    assert "Maximum Flexibility" in content, "plan.md must evaluate Maximum Flexibility"
    assert "Default-Case Simplicity" in content, "plan.md must evaluate Default-Case Simplicity"


def test_plan_template_mandates_ousterhout_depth_and_adr_synthesis(repo_templates_dir: Path):
    plan_md = repo_templates_dir / "plan.md"
    content = plan_md.read_text(encoding="utf-8")
    assert "depth" in content.lower() or "ousterhout" in content.lower(), (
        "plan.md must evaluate module depth at the seam"
    )
    assert "ADR" in content, "plan.md must synthesize design trade-offs into an ADR"
