"""Registry of language parsers for universal codebase scanning."""

from __future__ import annotations

from pathlib import Path
from .base import BaseLanguageParser
from .python_parser import PythonParser
from .web_parser import WebParser
from .go_parser import GoParser
from .rust_parser import RustParser
from .jvm_parser import JVMParser
from .native_parser import NativeParser
from .data_ml_parser import DataMLParser

ALL_PARSERS: list[BaseLanguageParser] = [
    PythonParser(),
    WebParser(),
    GoParser(),
    RustParser(),
    JVMParser(),
    NativeParser(),
    DataMLParser(),
]


def get_parser_for_path(path: Path) -> BaseLanguageParser | None:
    """Find the appropriate language parser for a given file path."""
    for parser in ALL_PARSERS:
        if parser.can_parse(path):
            return parser
    return None
