"""Git-based sync engine for Platinum distributed vaults."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from agents.constants import (
    APPROVED_DIR,
    DASHBOARD_FILE,
    IN_PROGRESS_DIR,
    PLANS_DIR,
    REJECTED_DIR,
    UPDATES_DIR,
)
from agents.platinum.models import ConflictRecord, ConflictType, SyncResult, SyncState
from agents.platinum.sync_policy import classify_owner, is_forbidden_path


@dataclass
class PreflightResult:
    blocked: bool
    forbidden: list[str]
    local_owned: list[str]


class GitSyncManager:
    def __init__(self, repo_root: Path, node_id: str, remote: str = "origin", branch: str = "main"):
        self.repo_root = repo_root
        self.node_id = node_id
        self.remote = remote
        self.branch = branch

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=self.repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def _changed_files(self) -> list[Path]:
        proc = self._run(["git", "status", "--porcelain"])
        files: list[Path] = []
        for line in proc.stdout.splitlines():
            if not line:
                continue
            path = line[3:]
            files.append(Path(path))
        return files

    def _ahead_behind(self) -> tuple[int, int]:
        proc = self._run(
            [
                "git",
                "rev-list",
                "--left-right",
                "--count",
                f"{self.remote}/{self.branch}...HEAD",
            ]
        )
        if proc.returncode != 0:
            return 0, 0
        parts = proc.stdout.strip().split()
        if len(parts) != 2:
            return 0, 0
        behind = int(parts[0])
        ahead = int(parts[1])
        return ahead, behind

    def preflight(self) -> PreflightResult:
        forbidden: list[str] = []
        local_owned: list[str] = []
        for path in self._changed_files():
            if is_forbidden_path(path):
                forbidden.append(str(path))
                continue
            owner = classify_owner(path)
            if owner == "local" and self.node_id == "cloud":
                local_owned.append(str(path))
        return PreflightResult(
            blocked=bool(forbidden or local_owned),
            forbidden=forbidden,
            local_owned=local_owned,
        )

    def _sync_state(
        self,
        result: SyncResult,
        started_at: datetime,
        finished_at: datetime,
        conflicted_files: list[str] | None = None,
        excluded_paths: list[str] | None = None,
    ) -> SyncState:
        ahead, behind = self._ahead_behind()
        latency = (datetime.utcnow() - finished_at).total_seconds()
        return SyncState(
            node_id=self.node_id,
            sync_started_at=started_at,
            sync_finished_at=finished_at,
            result=result,
            ahead_count=ahead,
            behind_count=behind,
            conflicted_files=conflicted_files or [],
            excluded_paths_detected=excluded_paths or [],
            latency_seconds=latency,
        )

    def _stage_allowed(self, files: Iterable[Path]) -> None:
        for path in files:
            if is_forbidden_path(path):
                continue
            self._run(["git", "add", "--", str(path)])

    def _commit_if_needed(self, message: str) -> None:
        diff = self._run(["git", "diff", "--cached", "--name-only"])
        if not diff.stdout.strip():
            return
        self._run(["git", "commit", "-m", message])

    def sync_once(self, message: str) -> SyncState:
        started_at = datetime.utcnow()
        preflight = self.preflight()
        if preflight.blocked:
            finished_at = datetime.utcnow()
            state = self._sync_state(
                SyncResult.BLOCKED,
                started_at,
                finished_at,
                excluded_paths=preflight.forbidden + preflight.local_owned,
            )
            self.emit_sync_status(state)
            return state
        files = self._changed_files()
        self._stage_allowed(files)
        self._commit_if_needed(message)
        self._run(["git", "fetch", "--all", "--prune"])
        pull = self._run(["git", "pull", "--rebase", self.remote, self.branch])
        if pull.returncode != 0:
            finished_at = datetime.utcnow()
            conflicts = self.resolve_conflicts()
            state = self._sync_state(
                SyncResult.CONFLICT,
                started_at,
                finished_at,
                conflicted_files=conflicts,
            )
            self.emit_sync_status(state)
            return state
        push = self._run(["git", "push", self.remote, self.branch])
        finished_at = datetime.utcnow()
        if push.returncode != 0:
            state = self._sync_state(SyncResult.FAILED, started_at, finished_at)
            self.emit_sync_status(state)
            return state
        state = self._sync_state(SyncResult.SUCCESS, started_at, finished_at)
        self.emit_sync_status(state)
        return state

    def resolve_conflicts(self) -> list[str]:
        conflicts: list[str] = []
        proc = self._run(["git", "diff", "--name-only", "--diff-filter=U"])
        for line in proc.stdout.splitlines():
            if not line:
                continue
            conflicts.append(line)
            conflict_type = self._classify_conflict(line)
            self._record_conflict(line, conflict_type)
            if conflict_type is ConflictType.PLAN:
                self._divert_plan_conflict(Path(line))
            if conflict_type is ConflictType.DASHBOARD and self.node_id == "cloud":
                self._divert_dashboard_conflict(Path(line))
        if conflicts:
            updates = self.repo_root / UPDATES_DIR / "conflicts"
            updates.mkdir(parents=True, exist_ok=True)
            path = updates / f"sync-conflict-{self.node_id}.txt"
            path.write_text("\n".join(conflicts), encoding="utf-8")
        return conflicts

    def _classify_conflict(self, path: str) -> ConflictType:
        if path.endswith(DASHBOARD_FILE):
            return ConflictType.DASHBOARD
        if path.startswith(PLANS_DIR + "/"):
            return ConflictType.PLAN
        if path.startswith(IN_PROGRESS_DIR + "/"):
            return ConflictType.CLAIM
        if path.startswith(APPROVED_DIR + "/") or path.startswith(REJECTED_DIR + "/"):
            return ConflictType.APPROVAL
        return ConflictType.GENERIC

    def _record_conflict(self, path: str, conflict_type: ConflictType) -> ConflictRecord:
        if conflict_type is ConflictType.DASHBOARD:
            winning = "local"
            resolution = "policy_resolved"
            notes = "local owns Dashboard.md"
        elif conflict_type is ConflictType.PLAN:
            winning = "manual_review"
            resolution = "manual_review"
            notes = "plan conflict diverted"
        else:
            winning = "manual_review"
            resolution = "manual_review"
            notes = "manual review required"
        record = ConflictRecord(
            conflict_id=str(uuid4()),
            file_path=path,
            conflict_type=conflict_type,
            winning_node=winning,
            losing_node=None,
            resolution_state=resolution,
            notes=notes,
        )
        conflicts_dir = self.repo_root / UPDATES_DIR / "conflicts"
        conflicts_dir.mkdir(parents=True, exist_ok=True)
        record_path = conflicts_dir / f"conflict-{record.conflict_id}.json"
        record_path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
        return record

    def _divert_plan_conflict(self, path: Path) -> None:
        updates_dir = self.repo_root / UPDATES_DIR / "plans"
        updates_dir.mkdir(parents=True, exist_ok=True)
        if path.exists():
            dest = updates_dir / f"{path.stem}.conflict.{self.node_id}{path.suffix}"
            dest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    def _divert_dashboard_conflict(self, path: Path) -> None:
        updates_dir = self.repo_root / UPDATES_DIR / "dashboard"
        updates_dir.mkdir(parents=True, exist_ok=True)
        if path.exists():
            dest = updates_dir / f"{path.stem}.conflict.{self.node_id}{path.suffix}"
            dest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    def emit_sync_status(self, state: SyncState) -> Path:
        updates = self.repo_root / UPDATES_DIR / "sync"
        updates.mkdir(parents=True, exist_ok=True)
        path = updates / f"{self.node_id}.json"
        path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
        return path
