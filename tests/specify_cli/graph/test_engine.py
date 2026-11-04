"""Tests for CodeGraphEngine."""

from __future__ import annotations

import json
from pathlib import Path
from specify_cli.graph.engine import CodeGraphEngine, sha256_file


def test_sha256_file(tmp_path: Path):
    f = tmp_path / "test.txt"
    f.write_text("hello world", encoding="utf-8")
    h1 = sha256_file(f)
    assert len(h1) == 64
    f.write_text("hello world 2", encoding="utf-8")
    h2 = sha256_file(f)
    assert h1 != h2


def test_engine_build_and_persistence(tmp_path: Path):
    # Setup files in tmp_path
    (tmp_path / "models.py").write_text(
        "from pydantic import BaseModel\nclass User(BaseModel):\n    name: str\n",
        encoding="utf-8",
    )
    (tmp_path / "api.py").write_text(
        "from fastapi import FastAPI\nimport models\napp = FastAPI()\n@app.get('/users')\ndef list_users():\n    return []\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_api.py").write_text(
        "import api\ndef test_users(): pass\n",
        encoding="utf-8",
    )

    engine = CodeGraphEngine(tmp_path)
    graph = engine.build()

    assert "models.py" in graph.files
    assert "api.py" in graph.files
    assert "tests/test_api.py" in graph.files

    # Verify routes & models extracted
    assert any(m.name == "User" for m in graph.models)
    assert any(r.path == "/users" for r in graph.routes)

    # Verify storage file written
    assert engine.graph_path.is_file()
    saved_data = json.loads(engine.graph_path.read_text(encoding="utf-8"))
    assert "models.py" in saved_data["files"]

    # Verify dependencies resolved
    assert "models.py" in graph.file_dependencies["api.py"]
    assert "api.py" in graph.reverse_file_dependencies["models.py"]
    assert "api.py" in graph.file_dependencies["tests/test_api.py"]
    assert "tests/test_api.py" in graph.reverse_file_dependencies["api.py"]


def test_engine_incremental_caching(tmp_path: Path):
    file1 = tmp_path / "service.py"
    file1.write_text("def run(): pass\n", encoding="utf-8")

    engine = CodeGraphEngine(tmp_path)
    engine.build()
    initial_hash = engine.graph.files["service.py"].sha256

    # Build again without changes
    engine.build()
    assert engine.graph.files["service.py"].sha256 == initial_hash

    # Modify file
    file1.write_text("def run_updated(): pass\n", encoding="utf-8")
    engine.build()
    new_hash = engine.graph.files["service.py"].sha256
    assert initial_hash != new_hash
    assert any("run_updated" in s for s in engine.graph.symbols)
    assert not any("service.py::run" == s for s in engine.graph.symbols)

    # Delete file
    file1.unlink()
    engine.build()
    assert "service.py" not in engine.graph.files
    assert not any(s.startswith("service.py::") for s in engine.graph.symbols)


def test_engine_blast_radius_and_search(tmp_path: Path):
    (tmp_path / "db.py").write_text("class Database: pass\n", encoding="utf-8")
    (tmp_path / "repo.py").write_text("import db\nclass UserRepo: pass\n", encoding="utf-8")
    (tmp_path / "service.py").write_text("import repo\nclass UserService: pass\n", encoding="utf-8")
    (tmp_path / "controller.py").write_text(
        "import service\nfrom fastapi import FastAPI\napp = FastAPI()\n@app.get('/users')\ndef get_u(): pass\n",
        encoding="utf-8",
    )
    (tmp_path / "test_service.py").write_text("import service\ndef test_srv(): pass\n", encoding="utf-8")

    engine = CodeGraphEngine(tmp_path)
    engine.build()

    # Query blast radius of db.py
    report = engine.query_blast_radius("db.py")
    assert report.target == "db.py"
    assert "repo.py" in report.directly_impacted_files
    assert "service.py" in report.transitively_impacted_files
    assert "controller.py" in report.transitively_impacted_files
    assert "test_service.py" in report.transitively_impacted_files
    assert any(r.path == "/users" for r in report.impacted_routes)
    assert any("test_service.py" in t for t in report.impacted_tests)
    assert report.risk_level in ("MEDIUM", "HIGH")

    # Search symbols
    syms = engine.search_symbols("UserRepo")
    assert len(syms) == 1
    assert syms[0].name == "UserRepo"

    syms_case = engine.search_symbols("user")
    assert len(syms_case) >= 2  # UserRepo, UserService

    # Query with bounded max_depth=1 (only direct dependents)
    report_depth1 = engine.query_blast_radius("db.py", max_depth=1)
    assert "repo.py" in report_depth1.directly_impacted_files
    assert len(report_depth1.transitively_impacted_files) == 0

    # Build with explicit worker count
    graph_par = engine.build(force=True, max_workers=2)
    assert len(graph_par.files) == 5

