"""Tests for SQLite GraphStorage backend."""

from __future__ import annotations

from pathlib import Path
from specify_cli.graph.models import ModelNode, RouteNode, SymbolNode, SymbolType
from specify_cli.graph.storage import GraphStorage


def test_storage_initialization_and_wal(tmp_path: Path):
    db_file = tmp_path / "test.db"
    storage = GraphStorage(db_file)
    assert db_file.is_file()

    # Verify tables created
    with storage._get_connection() as conn:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "files" in tables
        assert "symbols" in tables
        assert "routes" in tables
        assert "models" in tables
        assert "edges" in tables
        assert "symbols_fts" in tables


def test_storage_save_and_fts_search(tmp_path: Path):
    storage = GraphStorage(tmp_path / "test.db")

    sym1 = SymbolNode(
        id="src/auth.py::TokenService",
        file_path="src/auth.py",
        name="TokenService",
        symbol_type=SymbolType.CLASS,
        line_start=10,
        line_end=50,
        signature="class TokenService:",
        docstring="Handles JWT authentication and refresh tokens.",
    )
    sym2 = SymbolNode(
        id="src/auth.py::generate_token",
        file_path="src/auth.py",
        name="generate_token",
        symbol_type=SymbolType.FUNCTION,
        line_start=55,
        line_end=70,
        signature="def generate_token(user_id: str) -> str:",
        docstring="Generates a signed JWT session token.",
    )
    route = RouteNode(
        file_path="src/auth.py",
        method="POST",
        path="/api/auth/token",
        handler_symbol="generate_token",
        line=55,
    )
    model = ModelNode(
        file_path="src/auth.py",
        name="TokenPayload",
        kind="pydantic",
        fields=["user_id", "exp"],
        line=80,
    )

    storage.save_file_nodes(
        file_path="src/auth.py",
        language="python",
        sha256="hash123",
        size_bytes=1024,
        line_count=90,
        symbols=[sym1, sym2],
        routes=[route],
        models=[model],
    )

    # Check cached hashes
    hashes = storage.get_cached_hashes()
    assert hashes["src/auth.py"] == "hash123"

    # Check FTS5 search (search by token, docstring, or name)
    results = storage.search_symbols_fts("TokenService")
    assert len(results) == 1
    assert results[0].name == "TokenService"

    # Search by stem in docstring (e.g. 'refresh' or 'jwt')
    jwt_results = storage.search_symbols_fts("jwt")
    assert len(jwt_results) >= 1

    # Search routes and models
    routes = storage.get_routes()
    assert len(routes) == 1
    assert routes[0].path == "/api/auth/token"

    models = storage.get_models()
    assert len(models) == 1
    assert models[0].name == "TokenPayload"
    assert "user_id" in models[0].fields


def test_storage_recursive_cte_blast_radius(tmp_path: Path):
    storage = GraphStorage(tmp_path / "test.db")

    # Insert files
    for f in ["db.py", "repo.py", "service.py", "controller.py"]:
        storage.save_file_nodes(
            file_path=f,
            language="python",
            sha256="h",
            size_bytes=100,
            line_count=10,
            symbols=[],
            routes=[],
            models=[],
        )

    # Dependency chain: controller -> service -> repo -> db
    edges = [
        ("controller.py", "service.py", "imports"),
        ("service.py", "repo.py", "imports"),
        ("repo.py", "db.py", "imports"),
    ]
    storage.sync_edges(edges)

    # Blast radius of db.py using SQL Recursive CTE
    direct, transitive = storage.query_blast_radius_cte("db.py", max_depth=5)
    assert direct == ["repo.py"]
    assert "service.py" in transitive
    assert "controller.py" in transitive

    # Test Mermaid export
    mermaid = storage.to_mermaid(focus_file="db.py")
    assert "flowchart TD" in mermaid
    assert "db.py" in mermaid
    assert "repo.py" in mermaid
