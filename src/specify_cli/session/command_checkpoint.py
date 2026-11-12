"""CLI command adapter for ``specify session checkpoint``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from .._console import console
from ..bundles.project import find_project_root
from ._commands import session_app
from .checkpoint import (
    CHECKPOINT_FILE_NAME,
    SessionPhase,
    get_checkpoint_path,
    update_session_checkpoint,
)


@session_app.command("checkpoint")
def checkpoint(
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            "-p",
            help="Project root directory (defaults to current directory).",
        ),
    ] = Path("."),
    feature: Annotated[
        str | None,
        typer.Option(
            "--feature",
            "-f",
            help="Active feature name.",
        ),
    ] = None,
    feature_dir: Annotated[
        str | None,
        typer.Option(
            "--feature-dir",
            "-d",
            help="Path to the feature specification directory.",
        ),
    ] = None,
    branch: Annotated[
        str | None,
        typer.Option(
            "--branch",
            "-b",
            help="Active git branch.",
        ),
    ] = None,
    phase: Annotated[
        str | None,
        typer.Option(
            "--phase",
            help="Current SDLC phase (specify, clarify, plan, tasks, implement, converge).",
        ),
    ] = None,
    task_done: Annotated[
        str | None,
        typer.Option(
            "--task-done",
            help="Mark a task ID as completed (e.g. T001).",
        ),
    ] = None,
    task_active: Annotated[
        str | None,
        typer.Option(
            "--task-active",
            help="Set the currently active task ID.",
        ),
    ] = None,
    clear: Annotated[
        bool,
        typer.Option(
            "--clear",
            help="Clear and remove the existing session checkpoint.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output updated checkpoint as JSON.",
        ),
    ] = False,
) -> None:
    """Create, update, or clear the session continuity checkpoint."""
    project_root = find_project_root(path.resolve()) or path.resolve()
    checkpoint_file = get_checkpoint_path(project_root)

    if clear:
        if checkpoint_file.is_file():
            checkpoint_file.unlink()
            if json_output:
                console.print_json(data={"cleared": True})
            else:
                console.print("[green]✔ Cleared session checkpoint.[/green]")
        else:
            if json_output:
                console.print_json(data={"cleared": False, "note": "file not found"})
            else:
                console.print("[yellow]No checkpoint file to clear.[/yellow]")
        return

    validated_phase: SessionPhase | None = None
    if phase:
        allowed = {
            "specify",
            "clarify",
            "plan",
            "tasks",
            "implement",
            "converge",
            "unknown",
        }
        if phase.lower() not in allowed:
            console.print(
                f"[red]Error:[/red] Invalid phase '{phase}'. Must be one of: {', '.join(sorted(allowed))}"
            )
            raise typer.Exit(1)
        validated_phase = phase.lower()  # type: ignore

    updated = update_session_checkpoint(
        project_root,
        feature_name=feature,
        feature_directory=feature_dir,
        branch=branch,
        phase=validated_phase,
        completed_task=task_done,
        active_task=task_active,
    )

    if json_output:
        console.print_json(updated.model_dump_json())
    else:
        console.print(
            f"[bold green]✔ Session checkpoint updated at:[/bold green] `.specify/{CHECKPOINT_FILE_NAME}`\n"
            f"Feature: [cyan]{updated.feature_name}[/cyan] | Phase: [magenta]{updated.phase}[/magenta] | "
            f"Tasks Completed: [yellow]{len(updated.completed_tasks)}[/yellow]"
        )
