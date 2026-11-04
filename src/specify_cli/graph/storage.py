"""SQLite Knowledge Graph storage backend with Recursive CTE graph queries and FTS5 search."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import ModelNode, RouteNode, SymbolNode, SymbolType

GRAPH_DB_REL_PATH = Path(".specify") / "memory" / "code-graph.db"


class GraphStorage:
    """Manages SQLite storage for the Codebase Knowledge Graph."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Create tables, indexes, and FTS5 virtual table if not present."""
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    language TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    line_count INTEGER NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS edges (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    PRIMARY KEY (source_id, target_id, kind)
                );
                CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
                CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);

                CREATE TABLE IF NOT EXISTS symbols (
                    id TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    symbol_type TEXT NOT NULL,
                    line_start INTEGER NOT NULL,
                    line_end INTEGER NOT NULL,
                    signature TEXT,
                    docstring TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id);
                CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);

                CREATE TABLE IF NOT EXISTS routes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                    method TEXT NOT NULL,
                    path TEXT NOT NULL,
                    handler_symbol TEXT,
                    line INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_routes_file ON routes(file_id);
                CREATE INDEX IF NOT EXISTS idx_routes_path ON routes(path);

                CREATE TABLE IF NOT EXISTS models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    fields_json TEXT NOT NULL,
                    line INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_models_file ON models(file_id);
                CREATE INDEX IF NOT EXISTS idx_models_name ON models(name);

                CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
                    symbol_id UNINDEXED,
                    name,
                    signature,
                    docstring,
                    file_path,
                    tokenize = 'porter unicode61'
                );
                """
            )

    def get_cached_hashes(self) -> dict[str, str]:
        """Return dict of {file_path: sha256} for all indexed files."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT id, sha256 FROM files")
            return {row["id"]: row["sha256"] for row in cur.fetchall()}

    def save_file_nodes(
        self,
        file_path: str,
        language: str,
        sha256: str,
        size_bytes: int,
        line_count: int,
        symbols: list[SymbolNode],
        routes: list[RouteNode],
        models: list[ModelNode],
    ) -> None:
        """Insert or replace file metadata, symbols, routes, models, and FTS."""
        with self._get_connection() as conn:
            # Delete old entries
            conn.execute("DELETE FROM symbols_fts WHERE file_path = ?", (file_path,))
            conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_path,))
            conn.execute("DELETE FROM routes WHERE file_id = ?", (file_path,))
            conn.execute("DELETE FROM models WHERE file_id = ?", (file_path,))

            # Insert/replace file
            conn.execute(
                """
                INSERT OR REPLACE INTO files (id, language, sha256, size_bytes, line_count, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (file_path, language, sha256, size_bytes, line_count),
            )

            # Insert symbols & FTS
            for sym in symbols:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO symbols (id, file_id, name, symbol_type, line_start, line_end, signature, docstring)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sym.id,
                        file_path,
                        sym.name,
                        sym.symbol_type.value,
                        sym.line_start,
                        sym.line_end,
                        sym.signature or "",
                        sym.docstring or "",
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO symbols_fts (symbol_id, name, signature, docstring, file_path)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (sym.id, sym.name, sym.signature or "", sym.docstring or "", file_path),
                )

            # Insert routes
            for r in routes:
                conn.execute(
                    """
                    INSERT INTO routes (file_id, method, path, handler_symbol, line)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (file_path, r.method, r.path, r.handler_symbol or "", r.line),
                )

            # Insert models
            for m in models:
                conn.execute(
                    """
                    INSERT INTO models (file_id, name, kind, fields_json, line)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (file_path, m.name, m.kind, json.dumps(m.fields), m.line),
                )

    def delete_files(self, file_paths: list[str]) -> None:
        """Remove deleted files and their associated records."""
        if not file_paths:
            return
        with self._get_connection() as conn:
            for fp in file_paths:
                conn.execute("DELETE FROM symbols_fts WHERE file_path = ?", (fp,))
                conn.execute("DELETE FROM edges WHERE source_id = ? OR target_id = ?", (fp, fp))
                conn.execute("DELETE FROM files WHERE id = ?", (fp,))

    def sync_edges(self, edges_list: list[tuple[str, str, str]]) -> None:
        """Replace all dependency edges."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM edges")
            conn.executemany(
                "INSERT OR IGNORE INTO edges (source_id, target_id, kind) VALUES (?, ?, ?)",
                edges_list,
            )

    def query_blast_radius_cte(
        self,
        target_file: str,
        max_depth: int = 5,
    ) -> tuple[list[str], list[str]]:
        """Calculate direct and transitive dependents using native SQL Recursive Common Table Expression (CTE).

        Returns:
            Tuple of (direct_dependents, transitive_dependents)
        """
        cte_query = """
        WITH RECURSIVE blast_radius(file_path, depth) AS (
            -- Anchor: Files directly importing target_file
            SELECT source_id, 1
            FROM edges
            WHERE target_id = ? AND kind = 'imports'

            UNION

            -- Recursive Step: Files importing those dependents
            SELECT e.source_id, b.depth + 1
            FROM edges e
            JOIN blast_radius b ON e.target_id = b.file_path
            WHERE b.depth < ? AND e.kind = 'imports'
        )
        SELECT file_path, MIN(depth) as depth
        FROM blast_radius
        WHERE file_path != ?
        GROUP BY file_path
        ORDER BY depth, file_path;
        """
        with self._get_connection() as conn:
            cur = conn.execute(cte_query, (target_file, max_depth, target_file))
            rows = cur.fetchall()

        direct: list[str] = []
        transitive: list[str] = []
        for r in rows:
            fp = r["file_path"]
            if r["depth"] == 1:
                direct.append(fp)
            else:
                transitive.append(fp)

        return direct, transitive

    def search_symbols_fts(self, query: str, limit: int = 50) -> list[SymbolNode]:
        """Search symbols using SQLite FTS5 with BM25 ranking and fallback to LIKE."""
        clean_tokens = [t.replace('"', "").replace("'", "") for t in query.split() if t.strip()]
        if not clean_tokens:
            return []

        match_expr = " AND ".join(f"{t}*" for t in clean_tokens)
        results: list[SymbolNode] = []

        with self._get_connection() as conn:
            try:
                # Try FTS5 query with BM25 ranking
                cur = conn.execute(
                    """
                    SELECT s.id, s.file_id, s.name, s.symbol_type, s.line_start, s.line_end, s.signature, s.docstring
                    FROM symbols_fts f
                    JOIN symbols s ON f.symbol_id = s.id
                    WHERE symbols_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (match_expr, limit),
                )
                for r in cur.fetchall():
                    results.append(
                        SymbolNode(
                            id=r["id"],
                            file_path=r["file_id"],
                            name=r["name"],
                            symbol_type=SymbolType(r["symbol_type"]),
                            line_start=r["line_start"],
                            line_end=r["line_end"],
                            signature=r["signature"] or None,
                            docstring=r["docstring"] or None,
                        )
                    )
            except Exception:
                pass

            # If FTS returns nothing, fallback to LIKE
            if not results:
                like_expr = f"%{query.strip()}%"
                cur = conn.execute(
                    """
                    SELECT id, file_id, name, symbol_type, line_start, line_end, signature, docstring
                    FROM symbols
                    WHERE name LIKE ? OR id LIKE ?
                    LIMIT ?
                    """,
                    (like_expr, like_expr, limit),
                )
                for r in cur.fetchall():
                    results.append(
                        SymbolNode(
                            id=r["id"],
                            file_path=r["file_id"],
                            name=r["name"],
                            symbol_type=SymbolType(r["symbol_type"]),
                            line_start=r["line_start"],
                            line_end=r["line_end"],
                            signature=r["signature"] or None,
                            docstring=r["docstring"] or None,
                        )
                    )

        return results

    def get_routes(self, file_paths: list[str] | None = None) -> list[RouteNode]:
        """Fetch routes, optionally filtered by file paths."""
        with self._get_connection() as conn:
            if file_paths:
                placeholders = ",".join("?" for _ in file_paths)
                cur = conn.execute(
                    f"SELECT file_id, method, path, handler_symbol, line FROM routes WHERE file_id IN ({placeholders}) ORDER BY path",
                    file_paths,
                )
            else:
                cur = conn.execute(
                    "SELECT file_id, method, path, handler_symbol, line FROM routes ORDER BY path"
                )
            return [
                RouteNode(
                    file_path=r["file_id"],
                    method=r["method"],
                    path=r["path"],
                    handler_symbol=r["handler_symbol"] or None,
                    line=r["line"],
                )
                for r in cur.fetchall()
            ]

    def get_models(self) -> list[ModelNode]:
        """Fetch all data models and database schemas."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT file_id, name, kind, fields_json, line FROM models ORDER BY name"
            )
            return [
                ModelNode(
                    file_path=r["file_id"],
                    name=r["name"],
                    kind=r["kind"],
                    fields=json.loads(r["fields_json"] or "[]"),
                    line=r["line"],
                )
                for r in cur.fetchall()
            ]

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics of the knowledge graph."""
        with self._get_connection() as conn:
            total_files = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            total_symbols = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
            total_routes = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
            total_models = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
            updated_at = conn.execute("SELECT MAX(updated_at) FROM files").fetchone()[0] or ""

            languages: dict[str, int] = {}
            for r in conn.execute("SELECT language, COUNT(*) as c FROM files GROUP BY language"):
                languages[r["language"]] = r["c"]

        return {
            "total_files": total_files,
            "total_symbols": total_symbols,
            "total_routes": total_routes,
            "total_models": total_models,
            "languages": languages,
            "updated_at": str(updated_at),
        }

    def to_mermaid(self, focus_file: str | None = None, max_nodes: int = 40) -> str:
        """Generate Mermaid flowchart directly from SQLite edges and routes."""
        lines = ["flowchart TD"]

        def _clean_id(path: str) -> str:
            return "n_" + path.replace("/", "_").replace(".", "_").replace("-", "_")

        with self._get_connection() as conn:
            if focus_file:
                cur = conn.execute(
                    """
                    SELECT DISTINCT id FROM (
                        SELECT ? as id
                        UNION
                        SELECT target_id as id FROM edges WHERE source_id = ?
                        UNION
                        SELECT source_id as id FROM edges WHERE target_id = ?
                    )
                    """,
                    (focus_file, focus_file, focus_file),
                )
                nodes = [r["id"] for r in cur.fetchall()]
            else:
                cur = conn.execute(
                    """
                    SELECT id, (
                        (SELECT COUNT(*) FROM edges WHERE source_id = files.id) +
                        (SELECT COUNT(*) FROM edges WHERE target_id = files.id)
                    ) as degree
                    FROM files
                    ORDER BY degree DESC
                    LIMIT ?
                    """,
                    (max_nodes,),
                )
                nodes = [r["id"] for r in cur.fetchall()]

            if not nodes:
                return "flowchart TD"

            # Get route/model counts for node labels
            placeholders = ",".join("?" for _ in nodes)
            r_counts = {
                r["file_id"]: r["c"]
                for r in conn.execute(
                    f"SELECT file_id, COUNT(*) as c FROM routes WHERE file_id IN ({placeholders}) GROUP BY file_id",
                    nodes,
                ).fetchall()
            }
            m_counts = {
                r["file_id"]: r["c"]
                for r in conn.execute(
                    f"SELECT file_id, COUNT(*) as c FROM models WHERE file_id IN ({placeholders}) GROUP BY file_id",
                    nodes,
                ).fetchall()
            }

            for nid in nodes:
                name = nid.split("/")[-1]
                extra = ""
                if r_counts.get(nid, 0) > 0:
                    extra = f" ({r_counts[nid]} routes)"
                elif m_counts.get(nid, 0) > 0:
                    extra = f" ({m_counts[nid]} models)"
                lines.append(f'    {_clean_id(nid)}["{name}{extra}"]')

            # Edges between these nodes
            cur_edges = conn.execute(
                f"""
                SELECT source_id, target_id FROM edges
                WHERE source_id IN ({placeholders}) AND target_id IN ({placeholders})
                """,
                nodes + nodes,
            )
            for e in cur_edges.fetchall():
                lines.append(f"    {_clean_id(e['source_id'])} --> {_clean_id(e['target_id'])}")

        return "\n".join(lines)
