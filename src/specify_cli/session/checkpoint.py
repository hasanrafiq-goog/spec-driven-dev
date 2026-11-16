"""Session continuity and checkpointing for Spec Kit."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, Field

CHECKPOINT_FILE_NAME = "session-checkpoint.json"

SessionPhase = Literal[
    "specify",
    "clarify",
    "plan",
    "tasks",
    "implement",
    "converge",
    "debug",
    "unknown",
]


class SessionCheckpoint(BaseModel):
    feature_name: str
    feature_directory: str
    branch: str = ""
    phase: SessionPhase = "specify"
    completed_tasks: list[str] = Field(default_factory=list)
    active_task: str | None = None
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


def get_checkpoint_path(project_root: Path) -> Path:
    return project_root / ".specify" / CHECKPOINT_FILE_NAME


def load_session_checkpoint(project_root: Path) -> SessionCheckpoint | None:
    path = get_checkpoint_path(project_root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return SessionCheckpoint.model_validate(data)
    except Exception:
        # Corrupted or unparseable checkpoint detected; create timestamped backup before reset
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = path.parent / f"session-checkpoint.corrupt.{timestamp}.json"
        try:
            shutil.copy2(path, backup_path)
        except OSError:
            pass
        return None


def save_session_checkpoint(project_root: Path, checkpoint: SessionCheckpoint) -> Path:
    path = get_checkpoint_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.updated_at = datetime.now(timezone.utc).isoformat()
    content = checkpoint.model_dump_json(indent=2)

    # Write atomically via temp file in the same directory and rename
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as tf:
        temp_name = tf.name
        tf.write(content)
        tf.flush()
        os.fsync(tf.fileno())

    os.replace(temp_name, path)
    return path


def update_session_checkpoint(
    project_root: Path,
    *,
    feature_name: str | None = None,
    feature_directory: str | None = None,
    branch: str | None = None,
    phase: SessionPhase | None = None,
    completed_task: str | None = None,
    active_task: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> SessionCheckpoint:
    existing = load_session_checkpoint(project_root)
    if existing is None:
        existing = SessionCheckpoint(
            feature_name=feature_name or "default",
            feature_directory=feature_directory or "specs/default",
            branch=branch or "",
            phase=phase or "specify",
        )
    if feature_name is not None:
        existing.feature_name = feature_name
    if feature_directory is not None:
        existing.feature_directory = feature_directory
    if branch is not None:
        existing.branch = branch
    if phase is not None:
        existing.phase = phase
    if active_task is not None:
        existing.active_task = active_task
    if completed_task is not None:
        if completed_task not in existing.completed_tasks:
            existing.completed_tasks.append(completed_task)
        if existing.active_task == completed_task:
            existing.active_task = None
    if metadata:
        existing.metadata.update(metadata)

    save_session_checkpoint(project_root, existing)
    return existing
