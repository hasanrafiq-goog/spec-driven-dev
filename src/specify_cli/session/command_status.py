"""CLI command adapter for ``specify session status``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from .._console import console
from ..bundles.project import find_project_root
from ._commands import session_app
from .checkpoint import load_session_checkpoint


@session_app.command("status")
def status(
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            "-p",
            help="Project root directory (defaults to current directory).",
        ),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output status as machine-readable JSON.",
        ),
    ] = False,
) -> None:
    """Display the current session continuity checkpoint."""
    project_root = find_project_root(path.resolve()) or path.resolve()
    checkpoint = load_session_checkpoint(project_root)

    if checkpoint is None:
        if json_output:
            console.print_json(data={"active": False, "checkpoint": None})
        else:
            console.print(
                Panel(
                    "[yellow]No active session checkpoint found in `.specify/`.[/yellow]\n"
                    "Start a feature with `/speckit-specify` or `specify session checkpoint --feature <name>`.",
                    title="Session Continuity Status",
                )
            )
        return

    if json_output:
        console.print_json(checkpoint.model_dump_json())
        return

    table = Table(
        title="Active Session Checkpoint", show_header=True, header_style="bold cyan"
    )
    table.add_column("Property", style="bold")
    table.add_column("Value", style="green")

    table.add_row("Feature", checkpoint.feature_name)
    table.add_row("Feature Directory", checkpoint.feature_directory)
    table.add_row("Branch", checkpoint.branch or "(none)")
    table.add_row("Phase", checkpoint.phase)
    table.add_row("Active Task", checkpoint.active_task or "(none)")
    table.add_row(
        "Completed Tasks",
        f"{len(checkpoint.completed_tasks)} ({', '.join(checkpoint.completed_tasks) if checkpoint.completed_tasks else 'none'})",
    )
    table.add_row("Last Updated", checkpoint.updated_at)

    console.print(table)
