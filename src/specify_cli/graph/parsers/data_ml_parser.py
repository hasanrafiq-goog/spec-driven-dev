"""Data and Machine Learning parsers (Jupyter Notebooks, SQL, Proto, R)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from .base import BaseLanguageParser
from ..models import ModelNode, RouteNode, SymbolNode, SymbolType


class DataMLParser(BaseLanguageParser):
    language = "data_ml"
    extensions = {".ipynb", ".sql", ".proto", ".r", ".R"}

    PROTO_MESSAGE_RE = re.compile(r"""message\s+([A-Za-z0-9_]+)\s*\{""")
    PROTO_SERVICE_RE = re.compile(r"""service\s+([A-Za-z0-9_]+)\s*\{""")
    PROTO_RPC_RE = re.compile(r"""rpc\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*returns\s*\(([^)]*)\)""")
    SQL_TABLE_RE = re.compile(r"""CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:`|"|')?([A-Za-z0-9_]+)(?:`|"|')?\s*\(""", re.IGNORECASE)

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

        ext = path.suffix.lower()

        # Jupyter Notebook (.ipynb)
        if ext == ".ipynb":
            try:
                nb = json.loads(content)
                code_lines: list[str] = []
                for cell in nb.get("cells", []):
                    if cell.get("cell_type") == "code":
                        code_lines.extend(cell.get("source", []))
                joined_code = "".join(code_lines)
                # Extract Python-like imports from the notebook
                for m in re.finditer(r"""(?:from|import)\s+([A-Za-z0-9_.]+)""", joined_code):
                    imports.append(m.group(1))
                symbols.append(
                    SymbolNode(
                        id=f"{relative_path}::notebook_pipeline",
                        name=path.stem,
                        symbol_type=SymbolType.PIPELINE,
                        file_path=relative_path,
                        line_start=1,
                        line_end=len(code_lines),
                        docstring=f"Jupyter Notebook pipeline with {len(nb.get('cells', []))} cells",
                    )
                )
            except Exception:
                pass

        # Protobuf (.proto)
        elif ext == ".proto":
            for m in re.finditer(r"""import\s+['"]([^'"]+)['"];""", content):
                imports.append(m.group(1))

            for m in self.PROTO_MESSAGE_RE.finditer(content):
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
                models.append(
                    ModelNode(
                        name=name,
                        kind="proto_message",
                        file_path=relative_path,
                        fields=[],
                        line=line_no,
                    )
                )

            for m in self.PROTO_SERVICE_RE.finditer(content):
                name = m.group(1)
                line_no = content[:m.start()].count("\n") + 1
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

            for m in self.PROTO_RPC_RE.finditer(content):
                rpc_name = m.group(1)
                req = m.group(2)
                res = m.group(3)
                line_no = content[:m.start()].count("\n") + 1
                routes.append(
                    RouteNode(
                        method="gRPC",
                        path=rpc_name,
                        handler_symbol=f"({req}) -> {res}",
                        file_path=relative_path,
                        line=line_no,
                    )
                )

        # SQL (.sql)
        elif ext == ".sql":
            for m in self.SQL_TABLE_RE.finditer(content):
                table_name = m.group(1)
                line_no = content[:m.start()].count("\n") + 1
                symbols.append(
                    SymbolNode(
                        id=f"{relative_path}::{table_name}",
                        name=table_name,
                        symbol_type=SymbolType.MODEL,
                        file_path=relative_path,
                        line_start=line_no,
                        line_end=line_no,
                    )
                )
                models.append(
                    ModelNode(
                        name=table_name,
                        kind="sql_table",
                        file_path=relative_path,
                        fields=[],
                        line=line_no,
                    )
                )

        return imports, symbols, routes, models
