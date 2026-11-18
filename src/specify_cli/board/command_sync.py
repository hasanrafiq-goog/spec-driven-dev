"""CLI command adapter for ``specify board sync``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from .._console import console
from ._commands import board_app
from ._operation_sync import BoardSyncRequest, run_board_sync


@board_app.command("sync")
def sync(
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            "-p",
            help="Target project root directory (defaults to current directory).",
        ),
    ] = Path("."),
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Parse .specify/BOARD.md and inspect sync plan without calling remote trackers.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output sync result as JSON.",
        ),
    ] = False,
) -> None:
    """Synchronize local-canonical .specify/BOARD.md with the configured tracking backend."""
    result = run_board_sync(BoardSyncRequest(project_path=path.resolve(), dry_run=dry_run))

    if json_output:
        console.print_json(
            data={
                "success": result.success,
                "provider": result.provider,
                "cards_parsed": result.cards_parsed,
                "synced_count": result.synced_count,
                "queued_count": result.queued_count,
                "replayed_count": result.replayed_count,
                "warnings": result.warnings,
            }
        )
        return

    console.print(
        f"[green]✓[/green] Board sync ({result.provider}): {result.cards_parsed} cards parsed, "
        f"{result.synced_count} synced, {result.replayed_count} replayed, {result.queued_count} queued offline."
    )
    for warn in result.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warn}")
