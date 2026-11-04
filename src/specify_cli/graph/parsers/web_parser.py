"""TypeScript, JavaScript, JSX, TSX, Vue, and Svelte parser."""

from __future__ import annotations

import re
from pathlib import Path
from .base import BaseLanguageParser
from ..models import ModelNode, RouteNode, SymbolNode, SymbolType


class WebParser(BaseLanguageParser):
    language = "typescript_javascript"
    extensions = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte"}

    # Patterns
    IMPORT_RE = re.compile(r"""(?:import\s+.*?\s+from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\))""")
    CLASS_RE = re.compile(r"""(?:export\s+)?(?:default\s+)?class\s+([A-Za-z0-9_$]+)(?:\s+extends\s+([A-Za-z0-9_$]+))?(?:\s+implements\s+([A-Za-z0-9_$,\s]+))?""")
    INTERFACE_RE = re.compile(r"""(?:export\s+)?interface\s+([A-Za-z0-9_$]+)""")
    TYPE_RE = re.compile(r"""(?:export\s+)?type\s+([A-Za-z0-9_$]+)\s*=""")
    FUNCTION_RE = re.compile(r"""(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(([^)]*)\)""")
    CONST_FN_RE = re.compile(r"""(?:export\s+)?const\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*(?::\s*[^=>]+)?\s*=>""")
    EXPRESS_ROUTE_RE = re.compile(r"""(?:app|router)\.(get|post|put|delete|patch|options)\s*\(\s*['"]([^'"]+)['"]""")
    ZOD_SCHEMA_RE = re.compile(r"""(?:export\s+)?const\s+([A-Za-z0-9_$]+)\s*=\s*z\.object\s*\(\{([^}]+)\}\)""")

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

        # Imports
        for match in self.IMPORT_RE.finditer(content):
            target = match.group(1) or match.group(2)
            if target:
                imports.append(target)

        # Classes
        for match in self.CLASS_RE.finditer(content):
            name = match.group(1)
            line_no = content[:match.start()].count("\n") + 1
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

        # Interfaces & Types
        for match in self.INTERFACE_RE.finditer(content):
            name = match.group(1)
            line_no = content[:match.start()].count("\n") + 1
            symbols.append(
                SymbolNode(
                    id=f"{relative_path}::{name}",
                    name=name,
                    symbol_type=SymbolType.INTERFACE,
                    file_path=relative_path,
                    line_start=line_no,
                    line_end=line_no,
                )
            )

        for match in self.TYPE_RE.finditer(content):
            name = match.group(1)
            line_no = content[:match.start()].count("\n") + 1
            symbols.append(
                SymbolNode(
                    id=f"{relative_path}::{name}",
                    name=name,
                    symbol_type=SymbolType.TYPE,
                    file_path=relative_path,
                    line_start=line_no,
                    line_end=line_no,
                )
            )

        # Functions & Arrow Functions
        for match in self.FUNCTION_RE.finditer(content):
            name = match.group(1)
            params = match.group(2)
            line_no = content[:match.start()].count("\n") + 1
            symbols.append(
                SymbolNode(
                    id=f"{relative_path}::{name}",
                    name=name,
                    symbol_type=SymbolType.FUNCTION,
                    file_path=relative_path,
                    line_start=line_no,
                    line_end=line_no,
                    signature=f"({params})",
                )
            )

        for match in self.CONST_FN_RE.finditer(content):
            name = match.group(1)
            params = match.group(2)
            line_no = content[:match.start()].count("\n") + 1
            symbols.append(
                SymbolNode(
                    id=f"{relative_path}::{name}",
                    name=name,
                    symbol_type=SymbolType.FUNCTION,
                    file_path=relative_path,
                    line_start=line_no,
                    line_end=line_no,
                    signature=f"({params}) => ...",
                )
            )

        # Routes (Express / Fastify)
        for match in self.EXPRESS_ROUTE_RE.finditer(content):
            method = match.group(1).upper()
            route_path = match.group(2)
            line_no = content[:match.start()].count("\n") + 1
            routes.append(
                RouteNode(
                    method=method,
                    path=route_path,
                    file_path=relative_path,
                    line=line_no,
                )
            )

        # Next.js App Router (route.ts / route.js exports: GET, POST, etc.)
        if path.stem in {"route", "api"}:
            for method in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
                if re.search(rf"""export\s+(?:async\s+)?function\s+{method}\b""", content):
                    routes.append(
                        RouteNode(
                            method=method,
                            path=f"/{relative_path.replace('/route.ts', '').replace('/route.js', '')}",
                            file_path=relative_path,
                            line=1,
                        )
                    )

        # Zod Schemas
        for match in self.ZOD_SCHEMA_RE.finditer(content):
            name = match.group(1)
            raw_fields = match.group(2)
            fields = [f.split(":")[0].strip() for f in raw_fields.split(",") if ":" in f]
            line_no = content[:match.start()].count("\n") + 1
            models.append(
                ModelNode(
                    name=name,
                    kind="zod_schema",
                    file_path=relative_path,
                    fields=fields,
                    line=line_no,
                )
            )

        return imports, symbols, routes, models
