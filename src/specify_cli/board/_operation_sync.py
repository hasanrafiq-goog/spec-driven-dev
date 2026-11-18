"""Shared application operation for ``specify board sync``."""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .._init_options import resolve_board_provider
from .models import BoardCard, BoardSyncRequest, BoardSyncResult, QueuedBoardMutation

BOARD_REL_PATH = Path(".specify/BOARD.md")
QUEUE_REL_PATH = Path(".specify/board-sync-queue.json")

_CARD_HEADER_RE = re.compile(r"^- \[(?P<done>[ xX])\] \*\*\[(?P<fid>FEAT-[A-Za-z0-9_-]+)\]\*\* (?P<title>.+)$")
_META_LINE_RE = re.compile(r"^\s+- \*\*(?P<key>[^*]+)\*\*:\s*`?(?P<val>[^`\n]+)`?\s*$")


@dataclass(frozen=True)
class BoardOperationDescriptor:
    """Stable metadata shared by delivery adapters for board synchronization."""

    operation_id: Literal["board.sync"]
    contract_version: Literal["1"]
    capabilities: frozenset[Literal["local-read", "local-write", "network-optional"]]
    network_access: Literal["opt-in"]


BOARD_SYNC_OPERATION = BoardOperationDescriptor(
    operation_id="board.sync",
    contract_version="1",
    capabilities=frozenset({"local-read", "local-write", "network-optional"}),
    network_access="opt-in",
)


def parse_board_cards(board_text: str) -> list[BoardCard]:
    """Parse feature-level cards (``FEAT-*``) from ``.specify/BOARD.md``."""
    cards: list[BoardCard] = []
    current_section = ""
    current_card: BoardCard | None = None

    for line in board_text.splitlines():
        if line.startswith("## "):
            current_section = line[3:].strip()
            current_card = None
            continue

        header_match = _CARD_HEADER_RE.match(line)
        if header_match:
            current_card = BoardCard(
                feature_id=header_match.group("fid"),
                title=header_match.group("title").strip(),
                section=current_section,
                completed=header_match.group("done").lower() == "x",
            )
            cards.append(current_card)
            continue

        if current_card is not None:
            if line.startswith("- ["):
                current_card = None
                continue
            meta_match = _META_LINE_RE.match(line)
            if meta_match:
                key = meta_match.group("key").strip().lower()
                val = meta_match.group("val").strip()
                if key == "stage":
                    current_card.stage = val
                elif key == "status":
                    current_card.status = val
                elif key == "external-ref":
                    current_card.external_ref = val
    return cards


def set_card_external_ref(board_text: str, feature_id: str, external_ref: str) -> str:
    """Idempotently attach or update ``External-Ref`` on a feature card without touching other cards."""
    lines = board_text.splitlines(keepends=True)
    out: list[str] = []
    in_target_card = False
    replaced = False

    for line in lines:
        stripped = line.rstrip("\r\n")
        header_match = _CARD_HEADER_RE.match(stripped)
        if header_match:
            if in_target_card and not replaced:
                out.append(f"  - **External-Ref**: `{external_ref}`\n")
                replaced = True
            in_target_card = header_match.group("fid") == feature_id
            out.append(line)
            continue

        if in_target_card:
            if stripped.startswith("## ") or stripped.startswith("- ["):
                if not replaced:
                    out.append(f"  - **External-Ref**: `{external_ref}`\n")
                    replaced = True
                in_target_card = False
                out.append(line)
                continue
            meta_match = _META_LINE_RE.match(stripped)
            if meta_match and meta_match.group("key").strip().lower() == "external-ref":
                out.append(f"  - **External-Ref**: `{external_ref}`\n")
                replaced = True
                continue

        out.append(line)

    if in_target_card and not replaced:
        out.append(f"  - **External-Ref**: `{external_ref}`\n")

    return "".join(out)


def _load_queue(queue_path: Path) -> list[QueuedBoardMutation]:
    if not queue_path.exists():
        return []
    try:
        raw = json.loads(queue_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeError):
        return []
    if not isinstance(raw, list):
        return []
    items: list[QueuedBoardMutation] = []
    for entry in raw:
        if isinstance(entry, dict) and entry.get("feature_id") and entry.get("provider"):
            items.append(
                QueuedBoardMutation(
                    feature_id=str(entry["feature_id"]),
                    title=str(entry.get("title", "")),
                    section=str(entry.get("section", "")),
                    stage=str(entry.get("stage", "")),
                    status=str(entry.get("status", "")),
                    provider=str(entry["provider"]),
                    external_ref=entry.get("external_ref"),
                    queued_at=str(entry.get("queued_at", "")),
                )
            )
    return items


def _save_queue(queue_path: Path, queue: list[QueuedBoardMutation]) -> None:
    if not queue:
        if queue_path.exists():
            queue_path.unlink()
        return
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "feature_id": q.feature_id,
            "title": q.title,
            "section": q.section,
            "stage": q.stage,
            "status": q.status,
            "provider": q.provider,
            "external_ref": q.external_ref,
            "queued_at": q.queued_at,
        }
        for q in queue
    ]
    queue_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _sync_github_card(card: BoardCard) -> str:
    """Create or update a GitHub issue via ``GITHUB_TOKEN`` or ``gh`` CLI, returning ``gh#<num>``."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    title = f"[{card.feature_id}] {card.title}"
    body = f"Stage: {card.stage or 'N/A'}\nStatus: {card.status or 'N/A'}\nSection: {card.section}"
    state = "closed" if card.completed or card.status.upper() == "CONVERGED" else "open"

    if token and repo:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "specify-cli",
        }
        if card.external_ref and card.external_ref.startswith("gh#"):
            issue_num = card.external_ref.split("#", 1)[1]
            url = f"https://api.github.com/repos/{repo}/issues/{issue_num}"
            req = urllib.request.Request(
                url,
                data=json.dumps({"title": title, "body": body, "state": state}).encode("utf-8"),
                headers=headers,
                method="PATCH",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
            return card.external_ref

        url = f"https://api.github.com/repos/{repo}/issues"
        req = urllib.request.Request(
            url,
            data=json.dumps({"title": title, "body": body}).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            created = json.loads(resp.read().decode("utf-8"))
        return f"gh#{created['number']}"

    gh_bin = shutil.which("gh")
    if gh_bin:
        if card.external_ref and card.external_ref.startswith("gh#"):
            issue_num = card.external_ref.split("#", 1)[1]
            subprocess.run(
                [gh_bin, "issue", "edit", issue_num, "--title", title, "--body", body],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            return card.external_ref
        proc = subprocess.run(
            [gh_bin, "issue", "create", "--title", title, "--body", body],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        match = re.search(r"/issues/(\d+)", proc.stdout)
        if match:
            return f"gh#{match.group(1)}"
        return "gh#created"

    raise RuntimeError("Missing GITHUB_TOKEN/GITHUB_REPOSITORY or authenticated 'gh' CLI")


def _sync_jira_card(card: BoardCard) -> str:
    """Create or update a Jira issue via REST API, returning the Jira issue key."""
    base_url = os.environ.get("JIRA_BASE_URL", "").strip().rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "").strip()
    token = os.environ.get("JIRA_API_TOKEN", "").strip()
    project_key = os.environ.get("JIRA_PROJECT_KEY", "").strip()

    if not (base_url and email and token and (project_key or card.external_ref)):
        raise RuntimeError("Missing JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, or JIRA_PROJECT_KEY")

    auth = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
    headers = {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    summary = f"[{card.feature_id}] {card.title}"

    if card.external_ref and not card.external_ref.startswith("gh#"):
        url = f"{base_url}/rest/api/3/issue/{card.external_ref}"
        payload = {"fields": {"summary": summary}}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        return card.external_ref

    url = f"{base_url}/rest/api/3/issue"
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": "Story"},
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        created = json.loads(resp.read().decode("utf-8"))
    return str(created["key"])


def _sync_remote(provider: str, card: BoardCard) -> str:
    if provider == "github":
        return _sync_github_card(card)
    if provider == "jira":
        return _sync_jira_card(card)
    raise ValueError(f"Unsupported remote board provider: {provider}")


def run_board_sync(request: BoardSyncRequest) -> BoardSyncResult:
    """Execute the ``board.sync`` operation with offline queue buffering and idempotency."""
    project_path = Path(request.project_path).resolve()
    board_path = project_path / BOARD_REL_PATH
    queue_path = project_path / QUEUE_REL_PATH

    provider = request.provider_override or resolve_board_provider(project_path)
    if not board_path.exists():
        return BoardSyncResult(
            success=True,
            provider=provider,
            warnings=["No .specify/BOARD.md found; nothing to synchronize."],
        )

    board_text = board_path.read_text(encoding="utf-8")
    cards = parse_board_cards(board_text)

    if provider == "local" or request.dry_run:
        return BoardSyncResult(
            success=True,
            provider=provider,
            cards_parsed=len(cards),
            cards=cards,
        )

    warnings: list[str] = []
    synced_count = 0
    replayed_count = 0
    existing_queue = _load_queue(queue_path)
    queued_by_id: dict[str, QueuedBoardMutation] = {q.feature_id: q for q in existing_queue}
    updated_board_text = board_text

    # 1. Replay queued mutations first
    for q_id in list(queued_by_id.keys()):
        q_item = queued_by_id[q_id]
        card = BoardCard(
            feature_id=q_item.feature_id,
            title=q_item.title,
            section=q_item.section,
            stage=q_item.stage,
            status=q_item.status,
            external_ref=q_item.external_ref,
        )
        try:
            ext_ref = _sync_remote(q_item.provider, card)
            updated_board_text = set_card_external_ref(updated_board_text, card.feature_id, ext_ref)
            del queued_by_id[q_id]
            replayed_count += 1
        except (urllib.error.URLError, subprocess.SubprocessError, OSError, RuntimeError, ValueError) as exc:
            warnings.append(f"Queue replay deferred for {q_id}: {exc}")

    # 2. Mirror current cards
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for card in cards:
        try:
            ext_ref = _sync_remote(provider, card)
            if ext_ref and ext_ref != card.external_ref:
                card.external_ref = ext_ref
                updated_board_text = set_card_external_ref(updated_board_text, card.feature_id, ext_ref)
            synced_count += 1
        except (urllib.error.URLError, subprocess.SubprocessError, OSError, RuntimeError, ValueError) as exc:
            queued_by_id[card.feature_id] = QueuedBoardMutation(
                feature_id=card.feature_id,
                title=card.title,
                section=card.section,
                stage=card.stage,
                status=card.status,
                provider=provider,
                external_ref=card.external_ref,
                queued_at=now_iso,
            )
            warnings.append(f"Remote sync buffered offline for {card.feature_id}: {exc}")

    if updated_board_text != board_text:
        board_path.write_text(updated_board_text, encoding="utf-8")

    _save_queue(queue_path, list(queued_by_id.values()))

    return BoardSyncResult(
        success=True,
        provider=provider,
        cards_parsed=len(cards),
        synced_count=synced_count,
        queued_count=len(queued_by_id),
        replayed_count=replayed_count,
        cards=cards,
        warnings=warnings,
    )
