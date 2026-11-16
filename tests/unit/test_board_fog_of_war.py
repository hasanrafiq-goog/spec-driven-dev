"""Tests for Fog-of-War board integration and clarify multi-modal ambiguity resolution."""

from __future__ import annotations

import re
from pathlib import Path
import pytest


def parse_board_fog_items(board_text: str) -> list[dict[str, str]]:
    """Parse Fog-of-War items from BOARD.md content.

    Returns empty list if the section is not present (backward compatibility).
    """
    fog_header = "## 🌫️ Fog of War (Not Yet Specified)"
    if fog_header not in board_text:
        return []

    lines = board_text.splitlines()
    in_fog = False
    items: list[dict[str, str]] = []
    current_item: dict[str, str] = {}

    for line in lines:
        if line.startswith("## "):
            if line.strip() == fog_header:
                in_fog = True
                continue
            elif in_fog:
                # Next section started
                break

        if in_fog:
            item_match = re.match(r"^\s*-\s*\[ \]\s*\*\*\[(FOG-\d+)\]\*\*\s*(.*)$", line)
            if item_match:
                if current_item:
                    items.append(current_item)
                current_item = {"id": item_match.group(1), "title": item_match.group(2).strip()}
                continue

            if current_item:
                status_match = re.search(r"\*\*Status\*\*:\s*`?([A-Z_]+)`?", line)
                if status_match:
                    current_item["status"] = status_match.group(1)
                mode_match = re.search(r"\*\*Resolution Mode\*\*:\s*`?([A-Z_]+)`?", line)
                if mode_match:
                    current_item["resolution_mode"] = mode_match.group(1)

    if current_item:
        items.append(current_item)
    return items


def test_board_with_fog_of_war_parses_cleanly(sample_board_with_fog: Path):
    content = sample_board_with_fog.read_text(encoding="utf-8")
    items = parse_board_fog_items(content)
    assert len(items) == 1
    assert items[0]["id"] == "FOG-001"
    assert items[0]["title"] == "Explore streaming telemetry"
    assert items[0]["status"] == "UNCERTAIN"
    assert items[0]["resolution_mode"] == "RESEARCH"


def test_legacy_board_without_fog_of_war_parses_as_empty(sample_legacy_board_no_fog: Path):
    content = sample_legacy_board_no_fog.read_text(encoding="utf-8")
    items = parse_board_fog_items(content)
    assert items == []


def test_specify_command_template_initializes_fog_of_war_header(repo_templates_dir: Path):
    specify_md = repo_templates_dir / "specify.md"
    content = specify_md.read_text(encoding="utf-8")
    assert "## 🌫️ Fog of War (Not Yet Specified)" in content, (
        "specify.md MUST include '## 🌫️ Fog of War (Not Yet Specified)' in BOARD.md initialization"
    )


def test_clarify_command_template_supports_three_modes_and_scratchpad(repo_templates_dir: Path):
    clarify_md = repo_templates_dir / "clarify.md"
    content = clarify_md.read_text(encoding="utf-8")
    assert "Socratic Grilling" in content or "Mode A" in content
    assert "Research Subagent" in content or "Mode B" in content
    assert "Prototype Spike" in content or "Mode C" in content
    assert "spikes/" in content or "scratchpad" in content
