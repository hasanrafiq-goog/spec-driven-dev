"""Tests for repository source scanner."""

from __future__ import annotations

from pathlib import Path
from specify_cli.graph.scanner import get_repo_pathspec, scan_source_files


def test_scanner_discovers_supported_files(tmp_path: Path):
    # Setup test workspace
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "src" / "index.ts").write_text("console.log('hi')", encoding="utf-8")
    (tmp_path / "src" / "server.go").write_text("package main", encoding="utf-8")

    # Unsupported files
    (tmp_path / "README.md").write_text("# Readme", encoding="utf-8")
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n")

    files = scan_source_files(tmp_path)
    rel_files = [f.relative_to(tmp_path).as_posix() for f in files]

    assert "src/main.py" in rel_files
    assert "src/index.ts" in rel_files
    assert "src/server.go" in rel_files
    assert "README.md" not in rel_files
    assert "image.png" not in rel_files


def test_scanner_ignores_default_dirs(tmp_path: Path):
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "index.js").write_text("export default {}", encoding="utf-8")

    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "pip.py").write_text("# pip", encoding="utf-8")

    (tmp_path / "app.py").write_text("x = 1", encoding="utf-8")

    files = scan_source_files(tmp_path)
    rel_files = [f.relative_to(tmp_path).as_posix() for f in files]

    assert "app.py" in rel_files
    assert not any("node_modules" in f for f in rel_files)
    assert not any(".venv" in f for f in rel_files)


def test_scanner_respects_gitignore(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("ignored.py\nbuild_output/*\n*.generated.ts\n", encoding="utf-8")
    (tmp_path / "ignored.py").write_text("pass", encoding="utf-8")
    (tmp_path / "kept.py").write_text("pass", encoding="utf-8")

    (tmp_path / "build_output").mkdir()
    (tmp_path / "build_output" / "bundle.js").write_text("var a = 1;", encoding="utf-8")

    (tmp_path / "api.generated.ts").write_text("export const a = 1;", encoding="utf-8")

    spec = get_repo_pathspec(tmp_path)
    assert spec is not None

    files = scan_source_files(tmp_path)
    rel_files = [f.relative_to(tmp_path).as_posix() for f in files]

    assert "kept.py" in rel_files
    assert "ignored.py" not in rel_files
    assert "api.generated.ts" not in rel_files
    assert not any("build_output" in f for f in rel_files)


def test_scanner_skips_oversized_files(tmp_path: Path):
    normal = tmp_path / "normal.py"
    normal.write_text("x = 1\n", encoding="utf-8")

    huge = tmp_path / "huge.py"
    # Write 1.1 MB
    huge.write_bytes(b"#" * (1024 * 1024 + 100))

    files = scan_source_files(tmp_path)
    rel_files = [f.relative_to(tmp_path).as_posix() for f in files]

    assert "normal.py" in rel_files
    assert "huge.py" not in rel_files

