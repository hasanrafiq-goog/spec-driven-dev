"""Tests for /speckit-debug command registration, template structure, and dual-ramp routing."""

from __future__ import annotations

from pathlib import Path
import pytest

from specify_cli import SKILL_DESCRIPTIONS
from specify_cli.integrations.base import _CORE_COMMAND_TEMPLATE_ORDER


def test_debug_command_registered_in_core_template_order():
    assert "debug" in _CORE_COMMAND_TEMPLATE_ORDER, (
        "'debug' must be registered in _CORE_COMMAND_TEMPLATE_ORDER in specify_cli.integrations.base"
    )


def test_debug_command_registered_in_skill_descriptions():
    assert "debug" in SKILL_DESCRIPTIONS, (
        "'debug' must be present in SKILL_DESCRIPTIONS in specify_cli.__init__"
    )


def test_debug_template_exists_and_contains_fail_closed_hook(repo_templates_dir: Path):
    debug_md = repo_templates_dir / "debug.md"
    assert debug_md.exists(), "templates/commands/debug.md MUST exist as a core command template"
    content = debug_md.read_text(encoding="utf-8")
    assert "halt immediately with a fatal error" in content, (
        "debug.md must contain the standard fail-closed hook check"
    )


def test_debug_template_contains_four_phase_loop_and_anti_shotgun_rule(repo_templates_dir: Path):
    debug_md = repo_templates_dir / "debug.md"
    content = debug_md.read_text(encoding="utf-8")
    assert "Phase 1: Understand" in content
    assert "Phase 2: Hypothesize" in content
    assert "Phase 3: Isolate" in content
    assert "Phase 4: Output Diagnostic Bundle" in content or "Diagnostic Bundle" in content
    assert "DO NOT write fix code" in content, "debug.md must contain the anti-shotgun debugging rule"


def test_debug_template_defines_ramp_b_spec_evolution_and_ramp_a_fast_patch(repo_templates_dir: Path):
    debug_md = repo_templates_dir / "debug.md"
    content = debug_md.read_text(encoding="utf-8")
    assert "Ramp B" in content, "debug.md must define Ramp B (spec evolution)"
    assert "specs/FIX-" in content, "debug.md must seed a living spec folder for Ramp B"
    assert "Ramp A" in content, "debug.md must define Ramp A (fast patch)"
