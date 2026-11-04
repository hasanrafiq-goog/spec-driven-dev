"""C, C++, and C# parser extracting includes/usings, classes, structs, functions, and ASP.NET routes."""

from __future__ import annotations

import re
from pathlib import Path
from .base import BaseLanguageParser
from ..models import ModelNode, RouteNode, SymbolNode, SymbolType


class NativeParser(BaseLanguageParser):
    language = "c_cpp_csharp"
    extensions = {".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".cs"}

    INCLUDE_RE = re.compile(r"""#(?:include|import)\s+[<"]([^>"]+)[>"]""")
    USING_RE = re.compile(r"""using\s+([A-Za-z0-9_.]+);""")
    CLASS_RE = re.compile(r"""(?:public|private|internal|protected)?\s*(?:static|sealed|abstract)?\s*class\s+([A-Za-z0-9_]+)""")
    STRUCT_RE = re.compile(r"""(?:public|private|internal|protected)?\s*struct\s+([A-Za-z0-9_]+)""")
    CS_ROUTE_RE = re.compile(r"""\[Http(Get|Post|Put|Delete|Patch)\s*\(\s*['"]([^'"]+)['"]\s*\)\]""")

    def parse(
        self,
        path: Path,
        relative_path: str,
        content: str,
    ) -> tuple[list[str], list[SymbolNode], list[RouteNode], list[ModelNode]]:
        imports: list[str] = []
        symbols: list[SymbolNode] = []
        routes: list[RouteNode] = []
        models: list[ModelNode] = []

        # Includes & usings
        for m in self.INCLUDE_RE.finditer(content):
            imports.append(m.group(1))

        for m in self.USING_RE.finditer(content):
            imports.append(m.group(1))

        # Classes
        for m in self.CLASS_RE.finditer(content):
            name = m.group(1)
            line_no = content[:m.start()].count("\n") + 1
            symbols.append(
                SymbolNode(
                    id=f"{relative_path}::{name}",
                    name=name,
                    symbol_type=SymbolType.CLASS,
                    file_path=relative_path,
                    line_start=line_no,
                    line_end=line_no,
                )
            )

        # Structs
        for m in self.STRUCT_RE.finditer(content):
            name = m.group(1)
            line_no = content[:m.start()].count("\n") + 1
            symbols.append(
                SymbolNode(
                    id=f"{relative_path}::{name}",
                    name=name,
                    symbol_type=SymbolType.STRUCT,
                    file_path=relative_path,
                    line_start=line_no,
                    line_end=line_no,
                )
            )

        # ASP.NET Routes
        for m in self.CS_ROUTE_RE.finditer(content):
            method = m.group(1).upper()
            route_path = m.group(2)
            line_no = content[:m.start()].count("\n") + 1
            routes.append(
                RouteNode(
                    method=method,
                    path=route_path,
                    file_path=relative_path,
                    line=line_no,
                )
            )

        return imports, symbols, routes, models
