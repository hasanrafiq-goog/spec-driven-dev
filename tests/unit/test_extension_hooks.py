from __future__ import annotations

import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = REPO_ROOT / "templates" / "commands"

_HOOK_KEY = re.compile(r"`hooks\.(before|after)_[a-z_]+`")
_PARSE_FAILURE_LINE = re.compile(
    r"^.*If the YAML cannot be parsed or is invalid.*$", re.MULTILINE
)

HOOK_TEMPLATES = sorted(
    p.name
    for p in TEMPLATES_DIR.glob("*.md")
    if _HOOK_KEY.search(p.read_text(encoding="utf-8"))
)


def test_hook_templates_discovered() -> None:
    assert {"specify.md", "plan.md", "tasks.md", "implement.md", "converge.md"} <= set(
        HOOK_TEMPLATES
    )


@pytest.mark.parametrize("name", HOOK_TEMPLATES)
def test_unreadable_manifest_halts_immediately_fail_closed(name: str) -> None:
    text = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
    lines = _PARSE_FAILURE_LINE.findall(text)
    assert len(lines) >= 2, f"{name}: expected at least 2 hook parse failure lines, found {len(lines)}"

    for line in lines:
        assert "continue normally" not in line.lower(), (
            f"{name}: contains 'continue normally' on YAML error, violating fail-closed security"
        )
        assert ("halt" in line.lower() or "fatal" in line.lower()), (
            f"{name}: hook failure does not mandate immediate halt: {line}"
        )
