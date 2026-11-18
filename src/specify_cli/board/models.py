"""Data models for local-canonical board parsing and remote mirroring."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BoardCard:
    """Represents a feature card parsed from ``.specify/BOARD.md``."""

    feature_id: str
    title: str
    section: str
    completed: bool = False
    stage: str = ""
    status: str = ""
    external_ref: str | None = None


@dataclass
class QueuedBoardMutation:
    """Pending remote board mutation buffered in ``.specify/board-sync-queue.json``."""

    feature_id: str
    title: str
    section: str
    stage: str
    status: str
    provider: str
    external_ref: str | None = None
    queued_at: str = ""


@dataclass(frozen=True)
class BoardSyncRequest:
    """Typed request contract for ``board.sync``."""

    project_path: object
    dry_run: bool = False
    provider_override: str | None = None


@dataclass(frozen=True)
class BoardSyncResult:
    """Typed result contract for ``board.sync``."""

    success: bool
    provider: str
    cards_parsed: int = 0
    synced_count: int = 0
    queued_count: int = 0
    replayed_count: int = 0
    cards: list[BoardCard] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error_message: str | None = None
