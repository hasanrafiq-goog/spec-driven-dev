from __future__ import annotations

import os
from pathlib import Path

from specify_cli.session.checkpoint import (
    CHECKPOINT_FILE_NAME,
    SessionCheckpoint,
    load_session_checkpoint,
    save_session_checkpoint,
)


def test_save_session_checkpoint_is_atomic(tmp_path: Path, monkeypatch) -> None:
    """Verify that save_session_checkpoint uses atomic os.replace."""
    replaced = []
    original_replace = os.replace

    def mock_replace(src, dst):
        replaced.append((Path(src), Path(dst)))
        return original_replace(src, dst)

    monkeypatch.setattr(os, "replace", mock_replace)

    checkpoint = SessionCheckpoint(
        feature_name="atomic-test",
        feature_directory="specs/001-atomic",
        branch="main",
        phase="implement",
        completed_tasks=["T001"],
    )

    saved_path = save_session_checkpoint(tmp_path, checkpoint)
    assert saved_path == tmp_path / ".specify" / CHECKPOINT_FILE_NAME
    assert saved_path.is_file()

    # Must have invoked os.replace with a temporary file in the same directory
    assert len(replaced) == 1
    src, dst = replaced[0]
    assert dst == saved_path
    assert src.parent == saved_path.parent
    assert src.name != CHECKPOINT_FILE_NAME


def test_load_corrupted_checkpoint_creates_backup(tmp_path: Path) -> None:
    """Verify that an unparseable checkpoint file is backed up before reset."""
    checkpoint_dir = tmp_path / ".specify"
    checkpoint_dir.mkdir(parents=True)
    corrupt_file = checkpoint_dir / CHECKPOINT_FILE_NAME
    corrupt_file.write_text("{ unclosed json: truncated ...", encoding="utf-8")

    loaded = load_session_checkpoint(tmp_path)
    assert loaded is None

    # Verify that a backup file was created
    backups = list(checkpoint_dir.glob("session-checkpoint.corrupt.*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == corrupt_file.read_text(encoding="utf-8")
