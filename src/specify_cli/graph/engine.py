"""CodeGraphEngine orchestrates parsing, incremental caching, edge linking, and blast radius queries."""

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
        self.graph_path = self.project_root / GRAPH_STORAGE_REL_PATH
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
        """Persist graph to .specify/memory/code-graph.json."""
        self.graph.project_root = str(self.project_root)
        self.graph.updated_at = datetime.now(timezone.utc).isoformat()
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        self.graph_path.write_text(
            json.dumps(self.graph.model_dump(), indent=2),
            encoding="utf-8",
        )
        return self.graph_path

    def build(self, force: bool = False, max_workers: int | None = None) -> CodeGraph:
        """Build or incrementally update the codebase graph using parallel workers."""
        source_files = scan_source_files(self.project_root)
        current_file_set: set[str] = set()
        files_to_parse: list[tuple[Path, str, str]] = []

        for file_path in source_files:
            rel_posix = file_path.relative_to(self.project_root).as_posix()
            current_file_set.add(rel_posix)

            file_hash = sha256_file(file_path)
            cached_node = self.graph.files.get(rel_posix)

            # Skip unchanged files if not forced
            if not force and cached_node and cached_node.sha256 == file_hash:
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

                    # Remove old symbols for this file
                    old_sym_ids = [s_id for s_id in self.graph.symbols if s_id.startswith(f"{rel_posix}::")]
                    for old_id in old_sym_ids:
                        self.graph.symbols.pop(old_id, None)

                    # Store new symbols
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
        deleted_files = set(self.graph.files.keys()) - current_file_set
        for d_file in deleted_files:
            self.graph.files.pop(d_file, None)
            dead_syms = [s_id for s_id in self.graph.symbols if s_id.startswith(f"{d_file}::")]
            for d_sym in dead_syms:
                self.graph.symbols.pop(d_sym, None)

        # Aggregate routes and models
        all_routes: list[RouteNode] = []
        all_models: list[ModelNode] = []
        for f in self.graph.files.values():
            all_routes.extend(f.routes)
            all_models.extend(f.models)

        self.graph.routes = all_routes
        self.graph.models = all_models

        # Link file dependencies
        self._rebuild_dependencies()

        self.save()
        return self.graph

    def _rebuild_dependencies(self) -> None:
        """Resolve import references into file-to-file dependency edges."""
        deps: dict[str, list[str]] = {f: [] for f in self.graph.files}
        rev_deps: dict[str, list[str]] = {f: [] for f in self.graph.files}

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
                    cand = (Path(rel).parent / imp).as_posix()
                    for ext in (".ts", ".js", ".py", ".go", ".rs", ".tsx", ".jsx"):
                        if f"{cand}{ext}" in self.graph.files:
                            resolved = f"{cand}{ext}"
                            break
                        if f"{cand}/index{ext}" in self.graph.files:
                            resolved = f"{cand}/index{ext}"
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

        self.graph.file_dependencies = deps
        self.graph.reverse_file_dependencies = rev_deps

    def query_blast_radius(self, target: str, max_depth: int = 5) -> BlastRadiusReport:
        """Calculate blast radius and affected files/tests/routes for target bounded by max_depth."""
        # Target can be a file or a symbol
        target_file: str | None = None
        target_symbol: str | None = None

        if "::" in target:
            target_symbol = target
            target_file = target.split("::")[0]
        elif target in self.graph.files:
            target_file = target
        else:
            # Check if target is symbol name
            for s_id in self.graph.symbols:
                if s_id.endswith(f"::{target}") or s_id.endswith(f".{target}"):
                    target_symbol = s_id
                    target_file = s_id.split("::")[0]
                    break

        if not target_file:
            return BlastRadiusReport(
                target=target,
                target_type="unknown",
                risk_level="LOW",
            )

        # Directly impacted files (files importing target_file)
        direct_files = sorted(self.graph.reverse_file_dependencies.get(target_file, []))

        # Transitive dependents (BFS bounded by max_depth)
        transitive: set[str] = set()
        queue: list[tuple[str, int]] = [(f, 1) for f in direct_files]
        visited = set(direct_files)

        while queue:
            curr, depth = queue.pop(0)
            transitive.add(curr)
            if depth >= max_depth:
                continue
            for parent in self.graph.reverse_file_dependencies.get(curr, []):
                if parent not in visited and parent != target_file:
                    visited.add(parent)
                    queue.append((parent, depth + 1))

        all_affected_files = {target_file} | set(direct_files) | transitive

        # Impacted routes
        impacted_routes: list[RouteNode] = [
            r for r in self.graph.routes if r.file_path in all_affected_files
        ]

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
            transitively_impacted_files=sorted(transitive - set(direct_files)),
            impacted_symbols=impacted_syms,
            impacted_routes=impacted_routes,
            impacted_tests=impacted_tests,
            risk_level=risk,
        )

    def search_symbols(self, query: str, limit: int = 50) -> list[SymbolNode]:
        """Search symbols matching query tokens (case-insensitive substring match)."""
        tokens = [t.lower() for t in query.split() if t.strip()]
        if not tokens:
            return []
        results: list[SymbolNode] = []
        for s in self.graph.symbols.values():
            name_lower = s.name.lower()
            id_lower = s.id.lower()
            if all(t in name_lower or t in id_lower for t in tokens):
                results.append(s)
                if len(results) >= limit:
                    break
        return results
