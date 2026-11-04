"""Tests for CodeGraph models."""

from __future__ import annotations

from specify_cli.graph.models import (
    BlastRadiusReport,
    CodeGraph,
    FileNode,
    ModelNode,
    RouteNode,
    SymbolNode,
    SymbolType,
)


def test_symbol_node_creation():
    sym = SymbolNode(
        id="src/service.py:UserService",
        name="UserService",
        symbol_type=SymbolType.CLASS,
        file_path="src/service.py",
        line_start=10,
        line_end=50,
        docstring="Handles user logic",
        references=["UserRepository"],
    )
    assert sym.name == "UserService"
    assert sym.symbol_type == SymbolType.CLASS
    assert sym.line_start == 10
    assert sym.line_end == 50
    assert sym.references == ["UserRepository"]


def test_file_node_creation():
    fn = FileNode(
        path="src/service.py",
        language="python",
        sha256="abc123hash",
        size_bytes=1024,
        line_count=50,
        symbols=["src/service.py:login"],
        imports=["os", "sys"],
        routes=[
            RouteNode(method="POST", path="/api/login", handler_symbol="login", file_path="src/service.py", line=5)
        ],
        models=[
            ModelNode(name="User", kind="pydantic", file_path="src/service.py", fields=["username", "email"], line=20)
        ],
    )
    assert fn.path == "src/service.py"
    assert len(fn.symbols) == 1
    assert len(fn.routes) == 1
    assert len(fn.models) == 1
    assert fn.imports == ["os", "sys"]


def test_codegraph_serialization_roundtrip():
    fn = FileNode(
        path="backend/main.py",
        language="python",
        sha256="hash999",
        size_bytes=2048,
        line_count=80,
        symbols=["backend/main.py:app"],
        imports=["fastapi"],
        routes=[
            RouteNode(method="GET", path="/health", handler_symbol="health_check", file_path="backend/main.py", line=10)
        ],
    )
    sym = SymbolNode(
        id="backend/main.py:app",
        name="app",
        symbol_type=SymbolType.VARIABLE,
        file_path="backend/main.py",
        line_start=1,
        line_end=1,
    )
    graph = CodeGraph(
        project_root="/workspace",
        updated_at="2026-11-04T12:00:00Z",
        files={"backend/main.py": fn},
        symbols={"backend/main.py:app": sym},
        routes=fn.routes,
        models=[],
        file_dependencies={"backend/main.py": ["backend/config.py"]},
        reverse_file_dependencies={"backend/config.py": ["backend/main.py"]},
    )

    summary = graph.summary()
    assert summary["total_files"] == 1
    assert summary["total_symbols"] == 1
    assert summary["total_routes"] == 1
    assert summary["languages"] == {"python": 1}

    # Serialization to JSON string and back
    json_data = graph.model_dump_json()
    restored = CodeGraph.model_validate_json(json_data)
    assert "backend/main.py" in restored.files
    assert restored.files["backend/main.py"].sha256 == "hash999"
    assert restored.file_dependencies["backend/main.py"] == ["backend/config.py"]
    assert restored.reverse_file_dependencies["backend/config.py"] == ["backend/main.py"]


def test_blast_radius_report_creation():
    report = BlastRadiusReport(
        target="src/auth.py",
        target_type="file",
        directly_impacted_files=["src/api.py"],
        transitively_impacted_files=["src/main.py"],
        impacted_symbols=["login_user"],
        impacted_routes=[
            RouteNode(method="POST", path="/login", handler_symbol="login", file_path="src/auth.py", line=20)
        ],
        impacted_tests=["tests/test_auth.py"],
        risk_level="HIGH",
    )
    assert report.target == "src/auth.py"
    assert report.risk_level == "HIGH"
    assert len(report.directly_impacted_files) == 1
    assert len(report.impacted_tests) == 1
