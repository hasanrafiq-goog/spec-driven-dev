"""Shared infrastructure and registration for ``specify session`` commands."""

from __future__ import annotations

import typer

session_app = typer.Typer(
    name="session",
    help="Manage session checkpoints and context continuity across agent runs.",
    no_args_is_help=True,
)


def register(app: typer.Typer) -> None:
    """Attach the session command group to the root Typer app."""
    # isort: off
    from . import command_status  # noqa: F401
    from . import command_checkpoint  # noqa: F401
    # isort: on

    app.add_typer(session_app, name="session")
