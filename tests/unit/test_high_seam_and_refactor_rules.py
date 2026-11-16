"""Tests for High-Seam Testing and Expand-Contract Refactoring rules."""

from __future__ import annotations

from pathlib import Path
import pytest


def test_spec_template_forbids_internal_file_paths_and_mandates_high_seams(repo_templates_dir: Path):
    specify_md = repo_templates_dir / "specify.md"
    spec_template_md = repo_templates_dir.parent / "spec-template.md"

    specify_content = specify_md.read_text(encoding="utf-8")
    spec_template_content = spec_template_md.read_text(encoding="utf-8")

    assert "file path" in specify_content.lower() and "seam" in specify_content.lower(), (
        "specify.md must mandate high module seams and forbid internal file paths"
    )
    assert "file path" in spec_template_content.lower() and "seam" in spec_template_content.lower(), (
        "spec-template.md must instruct developers to avoid brittle file paths and test high seams"
    )


def test_tasks_template_mandates_expand_contract_for_wide_refactors(repo_templates_dir: Path):
    tasks_md = repo_templates_dir / "tasks.md"
    tasks_template_md = repo_templates_dir.parent / "tasks-template.md"

    tasks_content = tasks_md.read_text(encoding="utf-8")
    tasks_template_content = tasks_template_md.read_text(encoding="utf-8")

    assert "expand–contract" in tasks_content.lower() or "expand-contract" in tasks_content.lower(), (
        "tasks.md must mandate Expand-Contract for wide refactors"
    )
    assert "expand–contract" in tasks_template_content.lower() or "expand-contract" in tasks_template_content.lower(), (
        "tasks-template.md must include Expand-Contract refactoring guidelines"
    )
    assert "phase 1: expand" in tasks_template_content.lower() or "expand" in tasks_template_content.lower()
    assert "phase 2: migrate" in tasks_template_content.lower() or "migrate" in tasks_template_content.lower()
    assert "phase 3: contract" in tasks_template_content.lower() or "contract" in tasks_template_content.lower()
