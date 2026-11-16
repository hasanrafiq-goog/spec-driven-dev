from __future__ import annotations

from pathlib import Path


def test_tasks_command_template_mandates_tdd_and_vertical_slicing() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tasks_cmd = repo_root / "templates" / "commands" / "tasks.md"
    assert tasks_cmd.exists(), f"Missing {tasks_cmd}"
    content = tasks_cmd.read_text(encoding="utf-8")

    # Contradiction checks: tests must not be marked optional
    assert "Tests are OPTIONAL" not in content, (
        "templates/commands/tasks.md still contains 'Tests are OPTIONAL'"
    )
    assert "tests requested" not in content.lower(), (
        "templates/commands/tasks.md contains conditional test phrasing ('tests requested')"
    )

    # Positive checks: mandatory TDD and vertical tracer bullet slicing
    assert "Vertical Tracer-Bullet Slicing" in content
    assert "Red-Green-Refactor" in content or "failing test" in content.lower()
    assert "3 files" in content


def test_tasks_template_markdown_mandates_tdd() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tasks_template = repo_root / "templates" / "tasks-template.md"
    assert tasks_template.exists(), f"Missing {tasks_template}"
    content = tasks_template.read_text(encoding="utf-8")

    assert "Tests are OPTIONAL" not in content, (
        "templates/tasks-template.md still contains 'Tests are OPTIONAL'"
    )
    assert "(OPTIONAL - only if tests requested)" not in content, (
        "templates/tasks-template.md contains '(OPTIONAL - only if tests requested)'"
    )
