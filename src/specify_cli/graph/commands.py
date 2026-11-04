"""CLI commands for the Universal Codebase Knowledge Graph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import typer
from rich.table import Table

from .._console import console
from .engine import CodeGraphEngine

app = typer.Typer(
    name="graph",
    help="Universal Codebase Knowledge Graph for blast radius analysis and architecture inspection.",
    no_args_is_help=True,
)


def _get_engine(project_path: Optional[Path] = None) -> CodeGraphEngine:
    root = project_path or Path.cwd()
    return CodeGraphEngine(root)


@app.command("build")
def build_graph(
    refresh: bool = typer.Option(False, "--refresh", "-r", help="Force a full re-scan of all files"),
    workers: Optional[int] = typer.Option(None, "--workers", "-w", help="Number of parallel worker threads"),
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Project root directory"),
) -> None:
    """Build or incrementally update the codebase knowledge graph."""
    engine = _get_engine(path)
    console.print(f"[bold blue]Indexing codebase at:[/bold blue] {engine.project_root}")
    graph = engine.build(force=refresh, max_workers=workers)
    summary = graph.summary()

    console.print(f"[bold green]✓ Code graph updated successfully![/bold green]")
    console.print(f"  • Files indexed: [cyan]{summary['total_files']}[/cyan]")
    console.print(f"  • Symbols extracted: [cyan]{summary['total_symbols']}[/cyan]")
    console.print(f"  • Routes detected: [cyan]{summary['total_routes']}[/cyan]")
    console.print(f"  • Models/Schemas: [cyan]{summary['total_models']}[/cyan]")
    console.print(f"  • Stored at: [dim]{engine.graph_path}[/dim]")


@app.command("summary")
def show_summary(
    json_output: bool = typer.Option(False, "--json", help="Output summary as JSON"),
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Project root directory"),
) -> None:
    """Show architectural summary of the codebase knowledge graph."""
    engine = _get_engine(path)
    summary = engine.summary()

    if json_output:
        console.print(json.dumps(summary, indent=2))
        return

    console.print(f"\n[bold]🏛️ Codebase Knowledge Graph Summary[/bold]")
    console.print(f"Project: [cyan]{engine.project_root}[/cyan]")
    console.print(f"Database: [dim]{engine.db_path}[/dim]")
    console.print(f"Last updated: [dim]{summary['updated_at']}[/dim]\n")

    table = Table(title="Overview Metrics")
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right", style="cyan")
    table.add_row("Total Source Files", str(summary["total_files"]))
    table.add_row("Total Symbols (Classes/Functions/Structs)", str(summary["total_symbols"]))
    table.add_row("API Routes / Endpoints", str(summary["total_routes"]))
    table.add_row("Data Models / Schemas", str(summary["total_models"]))
    console.print(table)

    if summary["languages"]:
        lang_table = Table(title="Languages Detected")
        lang_table.add_column("Language", style="bold")
        lang_table.add_column("Files", justify="right", style="green")
        for lang, count in sorted(summary["languages"].items(), key=lambda x: -x[1]):
            lang_table.add_row(lang, str(count))
        console.print(lang_table)


@app.command("blast-radius")
def blast_radius(
    target: str = typer.Argument(..., help="File path or symbol name to analyze"),
    max_depth: int = typer.Option(5, "--max-depth", "-d", help="Maximum transitive traversal depth"),
    json_output: bool = typer.Option(False, "--json", help="Output report as JSON"),
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Project root directory"),
) -> None:
    """Calculate blast radius and affected files/tests/routes for an enhancement or refactor."""
    engine = _get_engine(path)
    report = engine.query_blast_radius(target, max_depth=max_depth)

    if json_output:
        console.print(json.dumps(report.model_dump(), indent=2))
        return

    risk_style = "red" if report.risk_level == "HIGH" else ("yellow" if report.risk_level == "MEDIUM" else "green")

    console.print(f"\n[bold]💥 Blast Radius Analysis for:[/bold] [cyan]{target}[/cyan]")
    console.print(f"Risk Assessment: [{risk_style} bold]{report.risk_level}[/{risk_style} bold]\n")

    console.print(f"[bold]Directly Impacted Files ({len(report.directly_impacted_files)}):[/bold]")
    if report.directly_impacted_files:
        for f in report.directly_impacted_files:
            console.print(f"  • {f}")
    else:
        console.print("  [dim]None (isolated file or no incoming imports)[/dim]")

    if report.transitively_impacted_files:
        console.print(f"\n[bold]Transitively Impacted Files ({len(report.transitively_impacted_files)}):[/bold]")
        for f in report.transitively_impacted_files:
            console.print(f"  • [dim]{f}[/dim]")

    if report.impacted_routes:
        console.print(f"\n[bold yellow]Affected API Routes ({len(report.impacted_routes)}):[/bold yellow]")
        for r in report.impacted_routes:
            console.print(f"  • [{r.method}] {r.path} ([dim]{r.file_path}:{r.line}[/dim])")

    if report.impacted_tests:
        console.print(f"\n[bold green]Relevant Test Suites ({len(report.impacted_tests)}):[/bold green]")
        for t in report.impacted_tests:
            console.print(f"  • {t}")


@app.command("routes")
def list_routes(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Project root directory"),
) -> None:
    """List all detected HTTP and RPC routes across the codebase."""
    engine = _get_engine(path)
    routes = engine.storage.get_routes()

    if json_output:
        console.print(json.dumps([r.model_dump() for r in routes], indent=2))
        return

    table = Table(title=f"Detected API Routes ({len(routes)})")
    table.add_column("Method", style="bold magenta")
    table.add_column("Path", style="bold")
    table.add_column("File", style="dim")
    table.add_column("Line", justify="right", style="cyan")

    for r in sorted(routes, key=lambda x: (x.path, x.method)):
        table.add_row(r.method, r.path, r.file_path, str(r.line))

    console.print(table)


@app.command("models")
def list_models(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Project root directory"),
) -> None:
    """List all detected data models, database tables, and schemas."""
    engine = _get_engine(path)
    models = engine.storage.get_models()

    if json_output:
        console.print(json.dumps([m.model_dump() for m in models], indent=2))
        return

    table = Table(title=f"Detected Models & Schemas ({len(models)})")
    table.add_column("Name", style="bold cyan")
    table.add_column("Kind", style="yellow")
    table.add_column("Fields", style="dim")
    table.add_column("File", style="dim")

    for m in sorted(models, key=lambda x: x.name):
        fields_str = ", ".join(m.fields[:5]) + ("..." if len(m.fields) > 5 else "")
        table.add_row(m.name, m.kind, fields_str or "-", f"{m.file_path}:{m.line}")

    console.print(table)


@app.command("query")
def query_symbols(
    query: str = typer.Argument(..., help="Search query (class, function, method name)"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of results to display"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Project root directory"),
) -> None:
    """Search for symbols across the knowledge graph."""
    engine = _get_engine(path)
    symbols = engine.search_symbols(query, limit=limit)

    if json_output:
        console.print(json.dumps([s.model_dump() for s in symbols], indent=2))
        return

    table = Table(title=f"Symbol Search Results for '{query}' ({len(symbols)})")
    table.add_column("Name", style="bold cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Signature", style="dim")
    table.add_column("File", style="dim")

    for s in sorted(symbols, key=lambda x: x.name):
        table.add_row(s.name, s.symbol_type.value, s.signature or "-", f"{s.file_path}:{s.line_start}")

    console.print(table)


@app.command("export")
def export_graph(
    format: str = typer.Option("mermaid", "--format", "-f", help="Export format: mermaid or json"),
    focus: Optional[str] = typer.Option(None, "--focus", help="Focus file or module for neighborhood diagram"),
    max_nodes: int = typer.Option(30, "--max-nodes", help="Max nodes in visual graph"),
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Project root directory"),
) -> None:
    """Export the codebase knowledge graph as a visual Mermaid diagram or JSON."""
    engine = _get_engine(path)
    if format.lower() == "mermaid":
        mermaid_code = engine.to_mermaid(focus_file=focus, max_nodes=max_nodes)
        console.print(mermaid_code)
    else:
        console.print(json.dumps(engine.graph.model_dump(), indent=2))

