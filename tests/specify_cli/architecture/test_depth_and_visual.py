"""Tests for Deletion Test, Two-Adapter Rule, --strict gating, and offline --visual HTML report."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import specify_cli
from specify_cli.architecture._operation_generate import (
    ArchitectureGenerateRequest,
    run_architecture_generate,
)

runner = CliRunner()


def test_depth_analyzer_flags_shallow_wrapper_and_single_adapter(tmp_path: Path) -> None:
    src = tmp_path / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "service.py").write_text(
        '''from abc import ABC, abstractmethod


class SingleAdapter(ABC):
    @abstractmethod
    def run(self) -> None:
        ...


class OnlyImpl(SingleAdapter):
    def run(self) -> None:
        return None


class ShallowProxy:
    def __init__(self, inner):
        self._inner = inner

    def execute(self, item):
        return self._inner.execute(item)
''',
        encoding="utf-8",
    )

    res = run_architecture_generate(
        ArchitectureGenerateRequest(project_path=tmp_path, visual=True, strict=False)
    )
    assert res.success is True
    assert res.summary is not None
    codes = {d.code for d in res.summary.diagnostics if not d.suppressed}
    assert "SHALLOW_PASS_THROUGH" in codes
    assert "PREMATURE_ABSTRACTION" in codes

    # Visual report exists and has zero external CDN links
    report_path = tmp_path / ".specify" / "reports" / "architecture.html"
    assert report_path.exists()
    html_text = report_path.read_text(encoding="utf-8")
    assert "<svg" in html_text
    assert "SHALLOW_PASS_THROUGH" in html_text
    assert "<script" not in html_text
    assert 'src="http' not in html_text
    assert 'href="http' not in html_text

    # Strict mode fails when unsuppressed diagnostics exist
    strict_res = run_architecture_generate(
        ArchitectureGenerateRequest(project_path=tmp_path, strict=True)
    )
    assert strict_res.success is False
    assert "Strict depth gate failed" in (strict_res.error_message or "")


def test_inline_suppression_markers_silence_diagnostics(tmp_path: Path) -> None:
    src = tmp_path / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "suppressed.py").write_text(
        '''from abc import ABC, abstractmethod


class IntentionalBase(ABC):  # arch: allow-single-adapter
    @abstractmethod
    def work(self) -> None:
        ...


class IntentionalFacade:  # arch: allow-shallow
    def __init__(self, target):
        self._target = target

    def call(self, x):
        return self._target.call(x)
''',
        encoding="utf-8",
    )

    res = run_architecture_generate(
        ArchitectureGenerateRequest(project_path=tmp_path, strict=True)
    )
    assert res.success is True
    assert res.summary is not None
    active = [d for d in res.summary.diagnostics if not d.suppressed]
    assert active == []


def test_cli_architecture_generate_visual_json(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
    result = runner.invoke(
        specify_cli.app,
        ["architecture", "generate", "--path", str(tmp_path), "--visual", "--json"],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["visual_report_path"] == ".specify/reports/architecture.html"
