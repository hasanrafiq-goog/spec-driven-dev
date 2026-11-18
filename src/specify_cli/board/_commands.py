"""Command-group registration for ``specify board``."""

from __future__ import annotations

import typer

board_app = typer.Typer(
    name="board",
    help="Synchronize local-canonical .specify/BOARD.md with configured SDLC tracking backends.",
    no_args_is_help=True,
)


def register(app: typer.Typer) -> None:
    """Register the ``board`` command group on the root Typer app."""
    from . import command_sync as _command_sync  # noqa: F401

    app.add_typer(board_app, name="board")
