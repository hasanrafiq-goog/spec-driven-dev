"""CodeGraphEngine orchestrates parsing, SQLite graph persistence, edge linking, and blast radius queries."""

from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import (
    BlastRadiusReport,
    CodeGraph,
    FileNode,
    ModelNode,
    RouteNode,
    SymbolNode,
)
from .parsers import get_parser_for_path
from .scanner import scan_source_files
from .storage import GRAPH_DB_REL_PATH, GraphStorage

GRAPH_STORAGE_REL_PATH = Path(".specify") / "memory" / "code-graph.json"


def sha256_file(path: Path) -> str:
    """Calculate sha256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _parse_file_task(
    file_path: Path,
    rel_posix: str,
    file_hash: str,
) -> tuple[str, str, str, int, int, list[str], list[SymbolNode], list[RouteNode], list[ModelNode]] | None:
    """Parse a single file. Helper for parallel worker pools."""
    parser = get_parser_for_path(file_path)
    if not parser:
        return None

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    imports, symbols, routes, models = parser.parse(file_path, rel_posix, content)
    line_count = len(content.splitlines())
    size_bytes = file_path.stat().st_size
    return (rel_posix, parser.language, file_hash, size_bytes, line_count, imports, symbols, routes, models)


class CodeGraphEngine:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.db_path = self.project_root / GRAPH_DB_REL_PATH
        self.graph_path = self.project_root / GRAPH_STORAGE_REL_PATH
        self.storage = GraphStorage(self.db_path)
        self.graph = self._load()

    def _load(self) -> CodeGraph:
        if self.graph_path.is_file():
            try:
                data = json.loads(self.graph_path.read_text(encoding="utf-8"))
                return CodeGraph.model_validate(data)
            except Exception:
                pass
        return CodeGraph(
            project_root=str(self.project_root),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def save(self) -> Path:
        """Persist graph to .specify/memory/code-graph.json for backward compatibility."""
        self.graph.project_root = str(self.project_root)
        self.graph.updated_at = datetime.now(timezone.utc).isoformat()
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        self.graph_path.write_text(
            json.dumps(self.graph.model_dump(), indent=2),
            encoding="utf-8",
        )
        return self.graph_path

    def build(self, force: bool = False, max_workers: int | None = None) -> CodeGraph:
        """Build or incrementally update the SQLite graph database using parallel workers."""
        source_files = scan_source_files(self.project_root)
        current_file_set: set[str] = set()
        files_to_parse: list[tuple[Path, str, str]] = []

        cached_hashes = self.storage.get_cached_hashes()

        for file_path in source_files:
            rel_posix = file_path.relative_to(self.project_root).as_posix()
            current_file_set.add(rel_posix)

            file_hash = sha256_file(file_path)
            cached_hash = cached_hashes.get(rel_posix)

            # Skip unchanged files if not forced
            if not force and cached_hash == file_hash and rel_posix in self.graph.files:
                continue

            files_to_parse.append((file_path, rel_posix, file_hash))

        # Parse dirty/new files in parallel across CPU cores
        if files_to_parse:
            workers = max_workers or min(32, (os.cpu_count() or 4) * 2)
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(_parse_file_task, f_path, r_posix, f_hash)
                    for f_path, r_posix, f_hash in files_to_parse
                ]
                for fut in futures:
                    res = fut.result()
                    if not res:
                        continue
                    (
                        rel_posix,
                        language,
                        file_hash,
                        size_bytes,
                        line_count,
                        imports,
                        symbols,
                        routes,
                        models,
                    ) = res

                    # Persist to SQLite
                    self.storage.save_file_nodes(
                        file_path=rel_posix,
                        language=language,
                        sha256=file_hash,
                        size_bytes=size_bytes,
                        line_count=line_count,
                        symbols=symbols,
                        routes=routes,
                        models=models,
                    )

                    # Update in-memory graph
                    old_sym_ids = [s_id for s_id in self.graph.symbols if s_id.startswith(f"{rel_posix}::")]
                    for old_id in old_sym_ids:
                        self.graph.symbols.pop(old_id, None)

                    for sym in symbols:
                        self.graph.symbols[sym.id] = sym

                    self.graph.files[rel_posix] = FileNode(
                        path=rel_posix,
                        language=language,
                        sha256=file_hash,
                        size_bytes=size_bytes,
                        line_count=line_count,
                        imports=imports,
                        symbols=[s.id for s in symbols],
                        routes=routes,
                        models=models,
                    )

        # Remove deleted files
        deleted_files = list(set(self.graph.files.keys()) - current_file_set)
        if deleted_files:
            self.storage.delete_files(deleted_files)
            for d_file in deleted_files:
                self.graph.files.pop(d_file, None)
                dead_syms = [s_id for s_id in self.graph.symbols if s_id.startswith(f"{d_file}::")]
                for d_sym in dead_syms:
                    self.graph.symbols.pop(d_sym, None)

        # Aggregate routes and models
        self.graph.routes = self.storage.get_routes()
        self.graph.models = self.storage.get_models()

        # Link file dependencies and persist edges in SQLite
        self._rebuild_dependencies()

        self.save()
        return self.graph

    def _rebuild_dependencies(self) -> None:
        """Resolve import references into file-to-file dependency edges and sync to SQLite."""
        deps: dict[str, list[str]] = {f: [] for f in self.graph.files}
        rev_deps: dict[str, list[str]] = {f: [] for f in self.graph.files}
        edge_tuples: list[tuple[str, str, str]] = []

        # Index known module names to posix paths
        module_to_file: dict[str, str] = {}
        for rel in self.graph.files:
            p = Path(rel)
            module_name = p.stem
            module_to_file[module_name] = rel
            dotted = rel.replace("/", ".").removesuffix(p.suffix)
            module_to_file[dotted] = rel

        for rel, node in self.graph.files.items():
            for imp in node.imports:
                # Direct relative resolution (e.g. ./utils, ../service)
                resolved: str | None = None
                if imp.startswith("."):
                    rel_dir = Path(rel).parent
                    normalized = os.path.normpath((rel_dir / imp).as_posix()).replace("\\", "/")
                    if normalized in self.graph.files:
                        resolved = normalized
                    else:
                        for ext in (".ts", ".tsx", ".d.ts", ".js", ".jsx", ".py", ".go", ".rs", ".mjs", ".cjs"):
                            if f"{normalized}{ext}" in self.graph.files:
                                resolved = f"{normalized}{ext}"
                                break
                            if f"{normalized}/index{ext}" in self.graph.files:
                                resolved = f"{normalized}/index{ext}"
                                break

                # Module/package resolution
                if not resolved:
                    # Check exact dotted match
                    if imp in module_to_file:
                        resolved = module_to_file[imp]
                    else:
                        base = imp.split(".")[0]
                        if base in module_to_file:
                            resolved = module_to_file[base]

                if resolved and resolved != rel and resolved not in deps[rel]:
                    deps[rel].append(resolved)
                    if rel not in rev_deps[resolved]:
                        rev_deps[resolved].append(rel)
                    edge_tuples.append((rel, resolved, "imports"))

        self.graph.file_dependencies = deps
        self.graph.reverse_file_dependencies = rev_deps
        self.storage.sync_edges(edge_tuples)

    def query_blast_radius(self, target: str, max_depth: int = 5) -> BlastRadiusReport:
        """Calculate blast radius using SQLite native Recursive Common Table Expression (CTE)."""
        target_file: str | None = None
        target_symbol: str | None = None

        if "::" in target:
            target_symbol = target
            target_file = target.split("::")[0]
        elif target in self.graph.files:
            target_file = target
        else:
            # Check if target is symbol name in SQLite
            matched = self.storage.search_symbols_fts(target, limit=1)
            if matched:
                target_symbol = matched[0].id
                target_file = matched[0].file_path

        if not target_file:
            return BlastRadiusReport(
                target=target,
                target_type="unknown",
                risk_level="LOW",
            )

        # Native SQL Recursive CTE query for downstream dependents
        direct_files, transitive_files = self.storage.query_blast_radius_cte(target_file, max_depth=max_depth)
        all_affected_files = [target_file] + direct_files + transitive_files

        # Impacted routes from SQLite
        impacted_routes = self.storage.get_routes(all_affected_files)

        # Impacted tests
        impacted_tests = [
            f for f in all_affected_files
            if "test" in f.lower() or "spec" in f.lower()
        ]

        # Impacted symbols
        impacted_syms = [
            s_id for s_id in self.graph.symbols
            if any(s_id.startswith(f"{f}::") for f in all_affected_files)
        ]

        # Risk assessment
        risk = "LOW"
        if len(all_affected_files) > 7 or len(impacted_routes) > 2:
            risk = "HIGH"
        elif len(all_affected_files) > 2 or len(impacted_routes) > 0:
            risk = "MEDIUM"

        return BlastRadiusReport(
            target=target,
            target_type="symbol" if target_symbol else "file",
            directly_impacted_files=direct_files,
            transitively_impacted_files=transitive_files,
            impacted_symbols=impacted_syms,
            impacted_routes=impacted_routes,
            impacted_tests=impacted_tests,
            risk_level=risk,
        )

    def search_symbols(self, query: str, limit: int = 50) -> list[SymbolNode]:
        """Search symbols using SQLite FTS5 full-text index with BM25 ranking."""
        return self.storage.search_symbols_fts(query, limit=limit)

    def summary(self) -> dict[str, Any]:
        """Return summary statistics directly from SQLite."""
        return self.storage.get_summary()

    def to_mermaid(self, focus_file: str | None = None, max_nodes: int = 40) -> str:
        """Export Mermaid diagram directly from SQLite graph edges."""
        return self.storage.to_mermaid(focus_file=focus_file, max_nodes=max_nodes)
