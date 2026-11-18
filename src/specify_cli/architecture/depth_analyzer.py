"""Static AST analyzer for Ousterhout module depth (Deletion Test) and Two-Adapter Rule."""

from __future__ import annotations

import ast
from pathlib import Path

from .models import ArchitectureDiagnostic

_ALLOW_SHALLOW_MARKER = "arch: allow-shallow"
_ALLOW_ADAPTER_MARKER = "arch: allow-single-adapter"


def _is_exempt_file(rel_path: str) -> bool:
    """Exempt test suites, Typer CLI adapters, and core base classes from shallow checks."""
    norm = rel_path.replace("\\", "/")
    parts = norm.split("/")
    filename = parts[-1]
    if "tests" in parts or filename.startswith("test_"):
        return True
    if filename.startswith("command_") or filename == "base.py":
        return True
    return False


def _has_marker(lines: list[str], lineno: int, marker: str) -> bool:
    """Return True if *marker* appears on the target line or the line immediately above it."""
    for idx in (lineno - 1, lineno - 2):
        if 0 <= idx < len(lines) and marker in lines[idx]:
            return True
    return False


def _is_pure_delegation_method(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if *fn* is a 1-to-1 pass-through call to ``self.<attr>.<method>(...)``."""
    body = list(fn.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]

    if len(body) != 1:
        return False

    stmt = body[0]
    call_node: ast.AST | None = None
    if isinstance(stmt, ast.Return):
        call_node = stmt.value
    elif isinstance(stmt, ast.Expr):
        call_node = stmt.value

    if isinstance(call_node, ast.Await):
        call_node = call_node.value

    if not isinstance(call_node, ast.Call):
        return False

    func = call_node.func
    if not isinstance(func, ast.Attribute):
        return False
    target = func.value
    return (
        isinstance(target, ast.Attribute)
        and isinstance(target.value, ast.Name)
        and target.value.id == "self"
    )


def _is_abstract_class(cls_node: ast.ClassDef) -> bool:
    """Return True if *cls_node* inherits from ABC, abc.ABC, or typing.Protocol."""
    for base in cls_node.bases:
        if isinstance(base, ast.Name) and base.id in ("ABC", "Protocol"):
            return True
        if isinstance(base, ast.Attribute) and base.attr in ("ABC", "Protocol"):
            return True
    for kw in cls_node.keywords:
        if (
            kw.arg == "metaclass"
            and isinstance(kw.value, (ast.Name, ast.Attribute))
            and getattr(kw.value, "id", getattr(kw.value, "attr", "")) == "ABCMeta"
        ):
            return True
    return False


def _base_names(cls_node: ast.ClassDef) -> list[str]:
    names: list[str] = []
    for base in cls_node.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return names


def analyze_python_depth(
    project_root: Path,
    python_rel_paths: list[str],
) -> list[ArchitectureDiagnostic]:
    """Run Deletion Test and Two-Adapter Rule checks across Python source files."""
    diagnostics: list[ArchitectureDiagnostic] = []
    abstract_defs: list[tuple[str, str, int, bool]] = []
    subclass_counts: dict[str, int] = {}

    for rel_path in sorted(python_rel_paths):
        full_path = project_root / rel_path
        if not full_path.is_file():
            continue
        try:
            source = full_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=rel_path)
        except (OSError, SyntaxError):
            continue

        lines = source.splitlines()
        exempt = _is_exempt_file(rel_path)

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            is_abs = _is_abstract_class(node)
            if not is_abs:
                for bname in _base_names(node):
                    subclass_counts[bname] = subclass_counts.get(bname, 0) + 1

            if exempt:
                continue

            if is_abs:
                suppressed = _has_marker(lines, node.lineno, _ALLOW_ADAPTER_MARKER)
                abstract_defs.append((rel_path, node.name, node.lineno, suppressed))
                continue

            methods = [
                item
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not (item.name.startswith("__") and item.name.endswith("__"))
            ]
            if methods and all(_is_pure_delegation_method(m) for m in methods):
                suppressed = _has_marker(lines, node.lineno, _ALLOW_SHALLOW_MARKER)
                diagnostics.append(
                    ArchitectureDiagnostic(
                        code="SHALLOW_PASS_THROUGH",
                        file_path=rel_path,
                        symbol_name=node.name,
                        line=node.lineno,
                        message=(
                            f"Class '{node.name}' delegates 1-to-1 with no added logic "
                            "(Deletion Test: consider inlining into callers)."
                        ),
                        suppressed=suppressed,
                    )
                )

    for rel_path, cls_name, lineno, suppressed in abstract_defs:
        count = subclass_counts.get(cls_name, 0)
        if count <= 1:
            diagnostics.append(
                ArchitectureDiagnostic(
                    code="PREMATURE_ABSTRACTION",
                    file_path=rel_path,
                    symbol_name=cls_name,
                    line=lineno,
                    message=(
                        f"Interface '{cls_name}' has {count} concrete implementation(s) "
                        "(Two-Adapter Rule: use concrete types until a second implementation exists)."
                    ),
                    suppressed=suppressed,
                )
            )

    return diagnostics
