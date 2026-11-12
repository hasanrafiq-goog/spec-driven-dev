"""Tests for Session Continuity Checkpointing (specify session ...)."""

from __future__ import annotations

from pathlib import Path
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.session.checkpoint import (
    CHECKPOINT_FILE_NAME,
    SessionCheckpoint,
    load_session_checkpoint,
    save_session_checkpoint,
    update_session_checkpoint,
)

runner = CliRunner()


def test_session_checkpoint_model_roundtrip(tmp_path: Path) -> None:
    checkpoint = SessionCheckpoint(
        feature_name="user-auth",
        feature_directory="specs/001-user-auth",
        branch="feat/user-auth",
        phase="implement",
        completed_tasks=["T001", "T002"],
        active_task="T003",
    )
    saved_path = save_session_checkpoint(tmp_path, checkpoint)
    assert saved_path == tmp_path / ".specify" / CHECKPOINT_FILE_NAME
    assert saved_path.is_file()

    loaded = load_session_checkpoint(tmp_path)
    assert loaded is not None
    assert loaded.feature_name == "user-auth"
    assert loaded.feature_directory == "specs/001-user-auth"
    assert loaded.branch == "feat/user-auth"
    assert loaded.phase == "implement"
    assert loaded.completed_tasks == ["T001", "T002"]
    assert loaded.active_task == "T003"


def test_update_session_checkpoint_incremental(tmp_path: Path) -> None:
    update_session_checkpoint(
        tmp_path,
        feature_name="payments",
        feature_directory="specs/payments",
        phase="tasks",
    )
    checkpoint = load_session_checkpoint(tmp_path)
    assert checkpoint is not None
    assert checkpoint.feature_name == "payments"
    assert checkpoint.phase == "tasks"

    # Mark a task done
    update_session_checkpoint(tmp_path, completed_task="T001", phase="implement")
    checkpoint = load_session_checkpoint(tmp_path)
    assert checkpoint is not None
    assert "T001" in checkpoint.completed_tasks
    assert checkpoint.phase == "implement"


def test_session_cli_commands(tmp_path: Path) -> None:
    # Initially status shows no checkpoint
    res = runner.invoke(app, ["session", "status", "--path", str(tmp_path)])
    assert res.exit_code == 0
    assert "No active session checkpoint" in res.output

    # JSON status
    res = runner.invoke(app, ["session", "status", "--path", str(tmp_path), "--json"])
    assert res.exit_code == 0
    assert '"active": false' in res.output

    # Create checkpoint via CLI
    res = runner.invoke(
        app,
        [
            "session",
            "checkpoint",
            "--path",
            str(tmp_path),
            "--feature",
            "billing",
            "--phase",
            "plan",
        ],
    )
    assert res.exit_code == 0
    assert "Session checkpoint updated" in res.output

    # Status shows billing
    res = runner.invoke(app, ["session", "status", "--path", str(tmp_path)])
    assert res.exit_code == 0
    assert "billing" in res.output
    assert "plan" in res.output

    # Update task done
    res = runner.invoke(
        app,
        [
            "session",
            "checkpoint",
            "--path",
            str(tmp_path),
            "--task-done",
            "T001",
        ],
    )
    assert res.exit_code == 0

    # Clear checkpoint
    res = runner.invoke(
        app, ["session", "checkpoint", "--path", str(tmp_path), "--clear"]
    )
    assert res.exit_code == 0
    assert "Cleared session checkpoint" in res.output
    assert load_session_checkpoint(tmp_path) is None
