"""Claim-by-move management for Platinum distributed tasks."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from agents.constants import IN_PROGRESS_DIR, NEEDS_ACTION_DIR, UPDATES_DIR
from agents.platinum.models import (
    ClaimState,
    ConflictRecord,
    ConflictType,
    SyncResult,
    SyncState,
    TaskClaim,
)


class ClaimManager:
    def __init__(self, vault_root: Path, node_id: str, lease_seconds: int = 600):
        self.vault_root = vault_root
        self.node_id = node_id
        self.lease_seconds = lease_seconds

    def claim_task(self, task_path: Path) -> TaskClaim:
        """Move task into /In_Progress/<agent>/ and write claim sidecar."""
        if task_path.parent.name != NEEDS_ACTION_DIR:
            raise ValueError("task must originate from Needs_Action")
        target_dir = self.vault_root / IN_PROGRESS_DIR / self.node_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / task_path.name
        task_path.replace(target_path)

        now = datetime.utcnow()
        claim = TaskClaim(
            task_id=task_path.stem,
            owner_node=self.node_id,
            claim_nonce=str(uuid4()),
            claimed_at=now,
            lease_expires_at=now + timedelta(seconds=self.lease_seconds),
            state=ClaimState.TENTATIVE,
            source_path=str(task_path),
            current_path=str(target_path),
            last_heartbeat_at=None,
        )
        self.write_claim_sidecar(target_path, claim)
        return claim

    def _sidecar_path(self, task_path: Path) -> Path:
        return task_path.with_suffix(task_path.suffix + ".claim.json")

    def write_claim_sidecar(self, task_path: Path, claim: TaskClaim) -> Path:
        sidecar = self._sidecar_path(task_path)
        sidecar.write_text(json.dumps(claim.to_dict(), indent=2), encoding="utf-8")
        return sidecar

    def read_claim_sidecar(self, task_path: Path) -> TaskClaim:
        sidecar = self._sidecar_path(task_path)
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        return TaskClaim(
            task_id=data["task_id"],
            owner_node=data["owner_node"],
            claim_nonce=data["claim_nonce"],
            claimed_at=datetime.fromisoformat(data["claimed_at"].replace("Z", "")),
            lease_expires_at=datetime.fromisoformat(
                data["lease_expires_at"].replace("Z", "")
            ),
            state=ClaimState(data["state"]),
            source_path=data["source_path"],
            current_path=data["current_path"],
            last_heartbeat_at=datetime.fromisoformat(
                data["last_heartbeat_at"].replace("Z", "")
            )
            if data.get("last_heartbeat_at")
            else None,
        )

    def confirm_claim(self, claim: TaskClaim, sync_state: SyncState) -> TaskClaim:
        """Transition a claim to committed after successful upstream sync."""
        if sync_state.result != SyncResult.SUCCESS:
            return claim
        now = datetime.utcnow()
        updated = replace(
            claim,
            state=ClaimState.COMMITTED,
            last_heartbeat_at=now,
            lease_expires_at=now + timedelta(seconds=self.lease_seconds),
        )
        self.write_claim_sidecar(Path(updated.current_path), updated)
        return updated

    def refresh_lease(self, claim: TaskClaim) -> TaskClaim:
        """Extend the claim lease while work remains active."""
        now = datetime.utcnow()
        next_state = claim.state
        if claim.state in {ClaimState.COMMITTED, ClaimState.ACTIVE}:
            next_state = ClaimState.ACTIVE
        updated = replace(
            claim,
            state=next_state,
            last_heartbeat_at=now,
            lease_expires_at=now + timedelta(seconds=self.lease_seconds),
        )
        self.write_claim_sidecar(Path(updated.current_path), updated)
        return updated

    def release_claim(self, claim: TaskClaim, outcome: str) -> TaskClaim:
        """Release or complete a claim with a final outcome."""
        if outcome == "completed":
            next_state = ClaimState.COMPLETED
        else:
            next_state = ClaimState.RELEASED
        updated = replace(
            claim,
            state=next_state,
            lease_expires_at=datetime.utcnow(),
        )
        self.write_claim_sidecar(Path(updated.current_path), updated)
        return updated

    def is_stale(self, claim: TaskClaim) -> bool:
        return datetime.utcnow() > claim.lease_expires_at

    def reconcile_claim_conflict(
        self, local_claim: TaskClaim, remote_claim: TaskClaim
    ) -> ConflictRecord:
        """Resolve conflicting claims and record the losing claim."""
        winner, loser = self._select_winner(local_claim, remote_claim)
        self._move_losing_claim(loser)
        record = ConflictRecord(
            conflict_id=str(uuid4()),
            file_path=loser.current_path,
            conflict_type=ConflictType.CLAIM,
            winning_node=winner.owner_node,
            losing_node=loser.owner_node,
            resolution_state="policy_resolved",
            notes="earliest claim wins",
        )
        self._write_conflict_record(record)
        return record

    def _select_winner(
        self, local_claim: TaskClaim, remote_claim: TaskClaim
    ) -> tuple[TaskClaim, TaskClaim]:
        if local_claim.claimed_at < remote_claim.claimed_at:
            return local_claim, remote_claim
        if local_claim.claimed_at > remote_claim.claimed_at:
            return remote_claim, local_claim
        if local_claim.claim_nonce <= remote_claim.claim_nonce:
            return local_claim, remote_claim
        return remote_claim, local_claim

    def _move_losing_claim(self, claim: TaskClaim) -> Path:
        conflicts_dir = self.vault_root / UPDATES_DIR / "conflicts" / "claims"
        node_dir = conflicts_dir / claim.owner_node
        node_dir.mkdir(parents=True, exist_ok=True)
        task_path = Path(claim.current_path)
        sidecar_path = self._sidecar_path(task_path)
        if task_path.exists():
            moved_task = node_dir / task_path.name
            task_path.replace(moved_task)
        else:
            moved_task = node_dir / task_path.name
        updated = replace(
            claim,
            state=ClaimState.TAKEN_OVER,
            current_path=str(moved_task),
        )
        self.write_claim_sidecar(moved_task, updated)
        if sidecar_path.exists():
            sidecar_path.replace(self._sidecar_path(moved_task))
        return moved_task

    def _write_conflict_record(self, record: ConflictRecord) -> Path:
        conflicts_dir = self.vault_root / UPDATES_DIR / "conflicts"
        conflicts_dir.mkdir(parents=True, exist_ok=True)
        path = conflicts_dir / f"claim-conflict-{record.conflict_id}.json"
        path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
        return path
