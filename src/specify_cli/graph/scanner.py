"""Repository scanner for discovering source files with .gitignore awareness."""

from __future__ import annotations

import os
from pathlib import Path
from pathspec import PathSpec
from .parsers import ALL_PARSERS

DEFAULT_IGNORED_DIRS = {
    ".git",
    ".specify",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
    "out",
    ".next",
    ".nuxt",
    ".gradle",
    ".idea",
    ".vscode",
}

SUPPORTED_EXTENSIONS = {ext for p in ALL_PARSERS for ext in p.extensions}
MAX_FILE_SIZE_BYTES = 1024 * 1024  # 1MB max file size to avoid minified/generated blobs


def get_repo_pathspec(project_root: Path) -> PathSpec | None:
    """Load .gitignore if present in project_root."""
    gitignore_file = project_root / ".gitignore"
    if gitignore_file.is_file():
        try:
            lines = gitignore_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            return PathSpec.from_lines("gitignore", lines)
        except Exception:
            pass
    return None


def scan_source_files(project_root: Path) -> list[Path]:
    """Scan project root for source code files supported by graph parsers."""
    spec = get_repo_pathspec(project_root)
    source_files: list[Path] = []

    for root, dirs, files in os.walk(project_root):
        # Exclude common large directories in-place for fast traversal
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORED_DIRS and not d.startswith(".")]

        rel_root = Path(root).relative_to(project_root)
        if str(rel_root) != "." and spec and spec.match_file(str(rel_root)):
            dirs[:] = []
            continue

        for f in files:
            path = Path(root) / f
            ext = path.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            try:
                if path.stat().st_size > MAX_FILE_SIZE_BYTES:
                    continue
            except OSError:
                continue

            rel_file = path.relative_to(project_root).as_posix()
            if spec and spec.match_file(rel_file):
                continue

            source_files.append(path)

    return sorted(source_files)
