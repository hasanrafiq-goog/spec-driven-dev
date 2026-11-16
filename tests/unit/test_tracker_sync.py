"""Tests for Local-First Issue Tracker Synchronization and Idempotent Metadata Comment Tagging."""

from __future__ import annotations

import re
from pathlib import Path
import pytest

TRACKER_COMMENT_RE = re.compile(r"<!--\s*tracker:([a-z_]+)#(\S+?)(?:\s+blocked_by:(\S+))?\s*-->")


def extract_tracker_metadata(task_line: str) -> dict[str, str | None] | None:
    """Extract tracker system and remote id from task line comment."""
    match = TRACKER_COMMENT_RE.search(task_line)
    if not match:
        return None
    return {
        "system": match.group(1),
        "remote_id": match.group(2),
        "blocked_by": match.group(3),
    }


def test_tracker_metadata_regex_matches_and_parses_cleanly():
    line = "- [ ] T001 Initialize database schema <!-- tracker:github#42 -->"
    meta = extract_tracker_metadata(line)
    assert meta is not None
    assert meta["system"] == "github"
    assert meta["remote_id"] == "42"
    assert meta["blocked_by"] is None

    line_with_dep = "- [x] T002 Implement repository <!-- tracker:linear#ENG-104 blocked_by:ENG-103 -->"
    meta2 = extract_tracker_metadata(line_with_dep)
    assert meta2 is not None
    assert meta2["system"] == "linear"
    assert meta2["remote_id"] == "ENG-104"
    assert meta2["blocked_by"] == "ENG-103"


def test_tasks_command_template_defines_local_default_and_comment_tagging(repo_templates_dir: Path):
    tasks_md = repo_templates_dir / "tasks.md"
    content = tasks_md.read_text(encoding="utf-8")
    assert "tracker: local" in content or "local-first" in content.lower(), (
        "tasks.md must specify that tracker defaults to local (100% offline)"
    )
    assert "<!-- tracker:" in content, (
        "tasks.md must document idempotent tracker comment tagging syntax <!-- tracker:... -->"
    )


def test_implement_command_template_contains_tracker_status_hook(repo_templates_dir: Path):
    implement_md = repo_templates_dir / "implement.md"
    content = implement_md.read_text(encoding="utf-8")
    assert "tracker" in content.lower(), (
        "implement.md must reference updating remote tracker issue status upon task completion"
    )


def test_converge_command_template_contains_tracker_epic_closure(repo_templates_dir: Path):
    converge_md = repo_templates_dir / "converge.md"
    content = converge_md.read_text(encoding="utf-8")
    assert "tracker" in content.lower(), (
        "converge.md must reference closing feature issue/epic in remote tracker upon convergence"
    )
