"""Antigravity (agy) integration — skills-based agent.

Antigravity uses ``.agents/skills/speckit-<name>/SKILL.md`` layout
(supported in Antigravity CLI v1.0.0+ and Antigravity IDE v2.0.0+).
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from ..base import SkillsIntegration

if TYPE_CHECKING:
    from ..manifest import IntegrationManifest


def _allow_all_tools() -> bool:
    """Return True if agy should run with auto-approved permissions in headless mode.

    Disabled by default for security. Set SPECKIT_AGY_ALLOW_ALL_TOOLS=1 (or
    SPECKIT_INTEGRATION_AGY_ALLOW_ALL_TOOLS=1) to enable.
    """
    for key in (
        "SPECKIT_INTEGRATION_AGY_ALLOW_ALL_TOOLS",
        "SPECKIT_AGY_ALLOW_ALL_TOOLS",
    ):
        val = os.environ.get(key)
        if val is not None and val.strip():
            return val.strip().lower() in ("1", "true", "yes", "on")
    return False


class AgyIntegration(SkillsIntegration):
    """Integration for Antigravity CLI and IDE.

    Inherits hook command normalization and post-processing from
    SkillsIntegration, ensuring slash commands constructed from dotted hook
    names are automatically converted to hyphenated skill invocations.
    """

    key: ClassVar[str] = "agy"
    config: ClassVar[dict[str, Any]] = {
        "name": "Antigravity",
        "folder": ".agents/",
        "commands_subdir": "skills",
        "install_url": "https://antigravity.google/",
        "requires_cli": True,
    }
    registrar_config: ClassVar[dict[str, Any]] = {
        "dir": ".agents/skills",
        "format": "markdown",
        "args": "$ARGUMENTS",
        "extension": "/SKILL.md",
    }

    def _resolve_executable(self) -> str:
        override = super()._resolve_executable()
        if override != self.key:
            return override
        if shutil.which("agy") is not None:
            return "agy"
        if shutil.which("jetski") is not None:
            return "jetski"
        return "agy"

    def build_exec_args(
        self,
        prompt: str,
        *,
        model: str | None = None,
        output_json: bool = True,
        integration_args: Sequence[str] | None = None,
        integration_options: Mapping[str, Any] | None = None,
        project_root: Path | None = None,
    ) -> list[str] | None:
        self.validate_runtime_config(integration_args, integration_options)
        args = [self._resolve_executable()]
        if _allow_all_tools():
            args.append("--dangerously-skip-permissions")
        if model:
            args.extend(["--model", model])
        if output_json:
            args.extend(["--output-format", "json"])
        if project_root is not None and str(project_root).strip():
            # agy requires an active workspace directory to discover skills under
            # .agents/skills/ when invoked from workflow directories (see issue #4480, PR #4481).
            args.extend(["--add-dir", str(Path(project_root).resolve())])
        # Honor SPECKIT_INTEGRATION_AGY_EXTRA_ARGS (operator-supplied flags).
        # Positioned before --print because agy consumes all trailing arguments
        # as prompt text (see #4480).
        self._apply_extra_args_env_var(args)
        args.extend(["--print", prompt])
        return args

    def setup(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        parsed_options: dict[str, Any] | None = None,
        **opts: Any,
    ) -> list[Path]:
        import click

        click.secho(
            "Warning: The .agents/ layout requires Antigravity CLI v1.0.0 or newer "
            "(or Antigravity IDE v2.0.0 or newer). "
            "Please ensure your installation is up to date.",
            fg="yellow",
            err=True,
        )
        created = super().setup(
            project_root, manifest, parsed_options=parsed_options, **opts
        )

        # Auto-generate GEMINI.md and AGENTS.md if they do not already exist
        # so Jetski and Antigravity immediately ingest project context and enforce constitution.md
        _ensure_gemini_context_files(project_root)

        # For Jetski and Antigravity UI slash-command discovery:
        # Link scaffolded skills into ~/.gemini/skills/ and ~/.gemini/config/skills/
        # so that the chat UI recognizes /speckit-* slash commands immediately.
        user_skills_dir = Path.home() / ".gemini" / "skills"
        user_config_skills_dir = Path.home() / ".gemini" / "config" / "skills"
        for target_dir in (user_skills_dir, user_config_skills_dir):
            if target_dir.is_dir():
                for skill_path in created:
                    if skill_path.name == "SKILL.md":
                        skill_folder = skill_path.parent
                        target_link = target_dir / skill_folder.name
                        try:
                            if target_link.is_symlink() or target_link.exists():
                                target_link.unlink()
                            target_link.symlink_to(skill_folder.resolve())
                        except OSError:
                            pass
        return created


GEMINI_MD_CONTENT = """# GEMINI.md - Spec-Driven Development Governance

This project follows **Spec-Driven Development (SDD)** governed by **Spec Kit** for Google Antigravity and Jetski.
Specifications, architectural plans, and task breakdowns are the **authoritative source of truth**. Code must conform to specifications, not vice-versa.

## 🏛️ Project Constitution & Core Principles
Before proposing architecture, breaking down tasks, or implementing code, you **MUST** read and strictly follow the principles defined in:
- [constitution.md](.specify/memory/constitution.md)

All implementations, testing bars, and code patterns must adhere to `.specify/memory/constitution.md` at all times.

## 🧭 Spec-Driven Workflow & Slash Commands
For any feature, enhancement, or bug fix, adhere to the phased lifecycle:
1. `/speckit-constitution` — Establish or update project constitution and quality gates
2. `/speckit-specify` — Create or update feature specification (`specs/<feature>/spec.md`)
3. `/speckit-clarify` — Identify underspecified areas and clarify requirements
4. `/speckit-plan` — Design technical implementation, architecture, and contracts (`specs/<feature>/plan.md`)
5. `/speckit-tasks` — Decompose plan into discrete, dependency-ordered tasks (`specs/<feature>/tasks.md`)
6. `/speckit-implement` — Execute tasks systematically with unit and integration tests
7. `/speckit-converge` — Self-healing loop to verify code matches spec and close gaps
8. `/speckit-analyze` — Validate cross-artifact consistency
9. `/speckit-checklist` — Generate quality verification checklists

## ⚡ Rules of Engagement for Jetski & Antigravity
- **Spec First**: Do not write application code or make architectural changes without an approved spec and tasks in `specs/`.
- **Active Feature**: Check `.specify/feature.json` (if present) for current active feature context.
- **Incremental Verification**: Implement task-by-task, verifying with tests after each step.
- **Constitution Authority**: If user instructions conflict with `.specify/memory/constitution.md`, highlight the conflict and seek clarification before proceeding.
"""

AGENTS_MD_CONTENT = """# AGENTS.md - Spec-Driven Development Governance

This project follows **Spec-Driven Development (SDD)** governed by **Spec Kit** for Google Antigravity and Jetski.
Specifications, architectural plans, and task breakdowns are the **authoritative source of truth**. Code must conform to specifications, not vice-versa.

## 🏛️ Project Constitution & Core Principles
Before proposing architecture, breaking down tasks, or implementing code, you **MUST** read and strictly follow the principles defined in:
- [constitution.md](.specify/memory/constitution.md)

All implementations, testing bars, and code patterns must adhere to `.specify/memory/constitution.md` at all times.

## 🧭 Spec-Driven Workflow & Slash Commands
For any feature, enhancement, or bug fix, adhere to the phased lifecycle:
1. `/speckit-constitution` — Establish or update project constitution and quality gates
2. `/speckit-specify` — Create or update feature specification (`specs/<feature>/spec.md`)
3. `/speckit-clarify` — Identify underspecified areas and clarify requirements
4. `/speckit-plan` — Design technical implementation, architecture, and contracts (`specs/<feature>/plan.md`)
5. `/speckit-tasks` — Decompose plan into discrete, dependency-ordered tasks (`specs/<feature>/tasks.md`)
6. `/speckit-implement` — Execute tasks systematically with unit and integration tests
7. `/speckit-converge` — Self-healing loop to verify code matches spec and close gaps
8. `/speckit-analyze` — Validate cross-artifact consistency
9. `/speckit-checklist` — Generate quality verification checklists

## ⚡ Rules of Engagement for Jetski & Antigravity
- **Spec First**: Do not write application code or make architectural changes without an approved spec and tasks in `specs/`.
- **Active Feature**: Check `.specify/feature.json` (if present) for current active feature context.
- **Incremental Verification**: Implement task-by-task, verifying with tests after each step.
- **Constitution Authority**: If user instructions conflict with `.specify/memory/constitution.md`, highlight the conflict and seek clarification before proceeding.
"""


def _ensure_gemini_context_files(project_root: Path) -> None:
    """Auto-generate GEMINI.md and AGENTS.md at project_root if they do not exist."""
    gemini_file = project_root / "GEMINI.md"
    agents_file = project_root / "AGENTS.md"

    if not gemini_file.exists():
        gemini_file.write_text(GEMINI_MD_CONTENT, encoding="utf-8")

    if not agents_file.exists():
        agents_file.write_text(AGENTS_MD_CONTENT, encoding="utf-8")

