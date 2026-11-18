"""Tests for ``specify init --board`` selection and persistence."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import specify_cli
from specify_cli._init_options import BOARD_PROVIDER_CHOICES, resolve_board_provider

runner = CliRunner()


def test_resolve_board_provider_defaults_to_local(tmp_path: Path) -> None:
    assert resolve_board_provider(tmp_path) == "local"

    opts_file = tmp_path / ".specify" / "init-options.json"
    opts_file.parent.mkdir(parents=True)
    opts_file.write_text(json.dumps({"board_provider": "jira"}), encoding="utf-8")
    assert resolve_board_provider(tmp_path) == "jira"

    opts_file.write_text(json.dumps({"board_provider": "unknown"}), encoding="utf-8")
    assert resolve_board_provider(tmp_path) == "local"


def test_init_rejects_invalid_board_provider(tmp_path: Path) -> None:
    result = runner.invoke(
        specify_cli.app,
        [
            "init",
            str(tmp_path / "proj"),
            "--integration",
            "agy",
            "--script",
            "sh",
            "--board",
            "invalid-tracker",
            "--non-interactive",
            "--ignore-agent-tools",
        ],
    )
    assert result.exit_code != 0
    assert "Invalid board backend" in result.output


def test_init_persists_board_provider_without_secrets(tmp_path: Path) -> None:
    proj = tmp_path / "my-proj"
    result = runner.invoke(
        specify_cli.app,
        [
            "init",
            str(proj),
            "--integration",
            "agy",
            "--script",
            "sh",
            "--board",
            "github",
            "--non-interactive",
            "--ignore-agent-tools",
        ],
    )
    assert result.exit_code == 0, result.output
    opts = json.loads((proj / ".specify" / "init-options.json").read_text(encoding="utf-8"))
    assert opts["board_provider"] == "github"
    assert "github_token" not in opts
    assert "jira_api_token" not in opts
    assert set(BOARD_PROVIDER_CHOICES.keys()) == {"local", "github", "jira"}
