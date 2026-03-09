"""Git-based sync engine for Platinum distributed vaults."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from agents.platinum.models import SyncResult, SyncState
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

    def _sync_state(self, result: SyncResult) -> SyncState:
        return SyncState(
            node_id=self.node_id,
            sync_started_at=datetime.utcnow(),
            sync_finished_at=datetime.utcnow(),
            result=result,
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
        preflight = self.preflight()
        if preflight.blocked:
            return self._sync_state(SyncResult.BLOCKED)
        files = self._changed_files()
        self._stage_allowed(files)
        self._commit_if_needed(message)
        self._run(["git", "fetch", "--all", "--prune"])
        pull = self._run(["git", "pull", "--rebase", self.remote, self.branch])
        if pull.returncode != 0:
            return self._sync_state(SyncResult.CONFLICT)
        push = self._run(["git", "push", self.remote, self.branch])
        if push.returncode != 0:
            return self._sync_state(SyncResult.FAILED)
        return self._sync_state(SyncResult.SUCCESS)

    def resolve_conflicts(self) -> list[str]:
        conflicts: list[str] = []
        proc = self._run(["git", "diff", "--name-only", "--diff-filter=U"])
        for line in proc.stdout.splitlines():
            if not line:
                continue
            conflicts.append(line)
        if conflicts:
            updates = self.repo_root / "Updates" / "conflicts"
            updates.mkdir(parents=True, exist_ok=True)
            path = updates / f"sync-conflict-{self.node_id}.txt"
            path.write_text("\n".join(conflicts), encoding="utf-8")
        return conflicts

    def emit_sync_status(self, state: SyncState) -> Path:
        updates = self.repo_root / "Updates" / "sync"
        updates.mkdir(parents=True, exist_ok=True)
        path = updates / f"{self.node_id}.json"
        path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
        return path
