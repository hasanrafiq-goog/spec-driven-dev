"""Tests for local-canonical ``BOARD.md`` parsing and idempotent ``specify board sync``."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

import specify_cli
from specify_cli.board._operation_sync import (
    BoardSyncRequest,
    parse_board_cards,
    run_board_sync,
    set_card_external_ref,
)

runner = CliRunner()

SAMPLE_BOARD = """# 📋 Project SDLC Board

## 🟡 Ready for Work
- [ ] **[FEAT-004]** Architectural Evolution Suite
  - **Type**: `Feature`
  - **Stage**: `Plan`
  - **Status**: `READY`

## ✅ Done & Converged (Historical Ledger)
- [x] **[FEAT-003]** Deep Socratic Grilling Engine
  - **Type**: `Feature`
  - **Stage**: `Converged`
  - **Status**: `CONVERGED`
  - **External-Ref**: `gh#33`
"""


def test_parse_and_idempotent_external_ref_preserves_history() -> None:
    cards = parse_board_cards(SAMPLE_BOARD)
    assert [c.feature_id for c in cards] == ["FEAT-004", "FEAT-003"]
    assert cards[1].external_ref == "gh#33"
    assert cards[1].completed is True

    updated = set_card_external_ref(SAMPLE_BOARD, "FEAT-004", "gh#44")
    assert "**External-Ref**: `gh#44`" in updated
    assert "**External-Ref**: `gh#33`" in updated

    # Re-applying updates the same card rather than duplicating lines
    updated_again = set_card_external_ref(updated, "FEAT-004", "gh#45")
    assert updated_again.count("gh#45") == 1
    assert "gh#44" not in updated_again


def test_board_sync_local_mode_makes_zero_network_calls(tmp_path: Path) -> None:
    spec_dir = tmp_path / ".specify"
    spec_dir.mkdir()
    (spec_dir / "BOARD.md").write_text(SAMPLE_BOARD, encoding="utf-8")
    (spec_dir / "init-options.json").write_text(
        json.dumps({"board_provider": "local"}), encoding="utf-8"
    )

    res = run_board_sync(BoardSyncRequest(project_path=tmp_path))
    assert res.success is True
    assert res.provider == "local"
    assert res.cards_parsed == 2
    assert res.synced_count == 0
    assert res.queued_count == 0


def test_board_sync_buffers_offline_and_replays_idempotently(tmp_path: Path) -> None:
    spec_dir = tmp_path / ".specify"
    spec_dir.mkdir()
    (spec_dir / "BOARD.md").write_text(SAMPLE_BOARD, encoding="utf-8")
    (spec_dir / "init-options.json").write_text(
        json.dumps({"board_provider": "jira"}), encoding="utf-8"
    )

    # Offline / missing credentials -> buffers cleanly without failing
    res_offline = run_board_sync(BoardSyncRequest(project_path=tmp_path))
    assert res_offline.success is True
    assert res_offline.queued_count == 2
    assert (spec_dir / "board-sync-queue.json").exists()

    # Online replay succeeds and attaches External-Ref idempotently
    with patch(
        "specify_cli.board._operation_sync._sync_remote",
        side_effect=lambda provider, card: card.external_ref or f"PROJ-{card.feature_id[-1]}",
    ):
        res_online = run_board_sync(BoardSyncRequest(project_path=tmp_path))

    assert res_online.success is True
    assert res_online.replayed_count == 2
    assert res_online.queued_count == 0
    assert not (spec_dir / "board-sync-queue.json").exists()
    board_after = (spec_dir / "BOARD.md").read_text(encoding="utf-8")
    assert "`PROJ-4`" in board_after
    assert "`gh#33`" in board_after


def test_board_sync_cli_json_output(tmp_path: Path) -> None:
    spec_dir = tmp_path / ".specify"
    spec_dir.mkdir()
    (spec_dir / "BOARD.md").write_text(SAMPLE_BOARD, encoding="utf-8")

    result = runner.invoke(
        specify_cli.app,
        ["board", "sync", "--path", str(tmp_path), "--dry-run", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["cards_parsed"] == 2
