"""Data models for the Universal Codebase Knowledge Graph."""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class SymbolType(str, Enum):
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    INTERFACE = "interface"
    STRUCT = "struct"
    MODEL = "model"
    ENDPOINT = "endpoint"
    TYPE = "type"
    ENUM = "enum"
    PIPELINE = "pipeline"
    VARIABLE = "variable"


class SymbolNode(BaseModel):
    id: str
    name: str
    symbol_type: SymbolType
    file_path: str
    line_start: int
    line_end: int
    docstring: str | None = None
    signature: str | None = None
    references: list[str] = Field(default_factory=list)
    decorators_or_annotations: list[str] = Field(default_factory=list)
    specified_in: str | None = None


class RouteNode(BaseModel):
    method: str
    path: str
    handler_symbol: str | None = None
    file_path: str
    line: int


class ModelNode(BaseModel):
    name: str
    kind: str
    file_path: str
    fields: list[str] = Field(default_factory=list)
    line: int


class FileNode(BaseModel):
    path: str
    language: str
    sha256: str
    size_bytes: int
    line_count: int
    imports: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    routes: list[RouteNode] = Field(default_factory=list)
    models: list[ModelNode] = Field(default_factory=list)


class CodeGraph(BaseModel):
    version: str = "1.0"
    project_root: str
    updated_at: str
    files: dict[str, FileNode] = Field(default_factory=dict)
    symbols: dict[str, SymbolNode] = Field(default_factory=dict)
    routes: list[RouteNode] = Field(default_factory=list)
    models: list[ModelNode] = Field(default_factory=list)
    file_dependencies: dict[str, list[str]] = Field(default_factory=dict)
    reverse_file_dependencies: dict[str, list[str]] = Field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        languages: dict[str, int] = {}
        for f in self.files.values():
            languages[f.language] = languages.get(f.language, 0) + 1
        return {
            "total_files": len(self.files),
            "total_symbols": len(self.symbols),
            "total_routes": len(self.routes),
            "total_models": len(self.models),
            "languages": languages,
            "updated_at": self.updated_at,
        }


class BlastRadiusReport(BaseModel):
    target: str
    target_type: str
    directly_impacted_files: list[str] = Field(default_factory=list)
    transitively_impacted_files: list[str] = Field(default_factory=list)
    impacted_symbols: list[str] = Field(default_factory=list)
    impacted_routes: list[RouteNode] = Field(default_factory=list)
    impacted_tests: list[str] = Field(default_factory=list)
    risk_level: str = "LOW"
