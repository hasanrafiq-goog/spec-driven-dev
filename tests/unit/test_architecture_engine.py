from __future__ import annotations

from pathlib import Path
import pytest

from specify_cli.architecture.engine import ArchitectureEngine
from specify_cli.architecture.models import FileNode


def test_discover_files_does_not_call_path_walk(tmp_path: Path, monkeypatch) -> None:
    """Ensure _discover_files works in Python 3.11 where Path.walk does not exist."""
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "app.py").write_text("print('hello')", encoding="utf-8")

    # In Python 3.11, Path has no walk attribute. Simulate by removing it.
    if hasattr(Path, "walk"):
        monkeypatch.delattr(Path, "walk")

    engine = ArchitectureEngine(tmp_path)
    code_files, spec_files, doc_files, ticket_files = engine._discover_files([], [])
    assert len(code_files) >= 1
    assert any("app.py" in str(p) for p in code_files)


def test_stem_collision_resolution_in_multi_module_repo(tmp_path: Path) -> None:
    """Verify that multiple files with identical stems (e.g. models.py) resolve to distinct paths."""
    auth_models = "src/auth/models.py"
    billing_models = "src/billing/models.py"
    billing_service = "src/billing/service.py"
    auth_service = "src/auth/service.py"

    files: dict[str, FileNode] = {
        auth_models: FileNode(
            path=auth_models,
            language="python",
            sha256="h1",
            size_bytes=100,
            line_count=10,
            imports=[],
            symbols=["User"],
        ),
        billing_models: FileNode(
            path=billing_models,
            language="python",
            sha256="h2",
            size_bytes=100,
            line_count=10,
            imports=["src.auth.models"],
            symbols=["Invoice"],
        ),
        billing_service: FileNode(
            path=billing_service,
            language="python",
            sha256="h3",
            size_bytes=100,
            line_count=10,
            imports=["src.billing.models"],
            symbols=["create_invoice"],
        ),
        auth_service: FileNode(
            path=auth_service,
            language="python",
            sha256="h4",
            size_bytes=100,
            line_count=10,
            imports=["src.auth.models"],
            symbols=["login"],
        ),
    }

    engine = ArchitectureEngine(tmp_path)
    file_deps = engine._resolve_file_dependencies(files)

    # billing_service imports src.billing.models -> must resolve to billing_models, NOT auth_models
    assert billing_models in file_deps[billing_service]
    assert auth_models not in file_deps[billing_service]

    # auth_service imports src.auth.models -> must resolve to auth_models, NOT billing_models
    assert auth_models in file_deps[auth_service]
    assert billing_models not in file_deps[auth_service]

    # billing_models imports src.auth.models -> must resolve to auth_models
    assert auth_models in file_deps[billing_models]
