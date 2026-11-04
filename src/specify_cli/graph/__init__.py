"""Universal Codebase Knowledge Graph subpackage for Spec Kit."""

from __future__ import annotations

import typer
from .commands import app as graph_app
from .engine import CodeGraphEngine
from .models import BlastRadiusReport, CodeGraph, FileNode, ModelNode, RouteNode, SymbolNode

__all__ = [
    "graph_app",
    "CodeGraphEngine",
    "CodeGraph",
    "FileNode",
    "SymbolNode",
    "RouteNode",
    "ModelNode",
    "BlastRadiusReport",
    "register",
]


def register(parent_app: typer.Typer) -> None:
    """Register the graph command group on the main specify app."""
    parent_app.add_typer(graph_app, name="graph")
