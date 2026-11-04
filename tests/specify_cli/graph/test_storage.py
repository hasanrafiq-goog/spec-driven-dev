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

    # Search by model field name (e.g. 'exp' or 'user_id') via synthesized summary in FTS
    field_results = storage.search_symbols_fts("user_id")
    assert len(field_results) >= 1
    assert any("TokenPayload" in r.name for r in field_results)

    # Search by endpoint path or handler via synthesized summary in FTS
    route_results = storage.search_symbols_fts("generate_token")
    assert len(route_results) >= 1


def test_storage_rich_semantic_synthesis(tmp_path: Path):
    """Verify rich semantic descriptions are synthesized and indexed for docstring-free code."""
    storage = GraphStorage(tmp_path / "test.db")

    # Undocumented function with structural facts
    sym = SymbolNode(
        id="src/payment.py::process_refund",
        file_path="src/payment.py",
        name="process_refund",
        symbol_type=SymbolType.FUNCTION,
        line_start=20,
        line_end=45,
        signature="def process_refund(transaction_id: str, amount_cents: int) -> bool:",
        docstring=None,  # No docstring!
        references=["stripe_client", "ledger_repo"],
        decorators_or_annotations=["@retry", "@require_admin"],
    )

    # Undocumented data model with fields
    model = ModelNode(
        file_path="src/payment.py",
        name="RefundReceipt",
        kind="dataclass",
        fields=["refund_id", "original_tx", "amount", "currency", "settled_at"],
        line=50,
    )

    # Undocumented route
    route = RouteNode(
        file_path="src/payment.py",
        method="POST",
        path="/v1/billing/refunds",
        handler_symbol="process_refund",
        line=20,
    )

    storage.save_file_nodes(
        file_path="src/payment.py",
        language="python",
        sha256="hash_refund",
        size_bytes=500,
        line_count=60,
        symbols=[sym],
        routes=[route],
        models=[model],
    )

    # 1. Search by reference or decorator found only in the synthesized summary
    res_retry = storage.search_symbols_fts("retry")
    assert len(res_retry) == 1
    assert res_retry[0].name == "process_refund"
    assert res_retry[0].summary is not None
    assert "stripe_client" in res_retry[0].summary

    # 2. Search by model field name (currency, settled_at) matches model
    res_field = storage.search_symbols_fts("settled_at")
    assert len(res_field) == 1
    assert res_field[0].name == "RefundReceipt"
    assert "amount" in (res_field[0].summary or "")

    # 3. Search by endpoint path fragment
    res_route = storage.search_symbols_fts("billing")
    assert len(res_route) >= 1
    assert any("/v1/billing/refunds" in r.name for r in res_route)


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
