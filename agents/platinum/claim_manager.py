"""Claim-by-move management for Platinum distributed tasks."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from agents.constants import IN_PROGRESS_DIR, NEEDS_ACTION_DIR
from agents.platinum.models import ClaimState, TaskClaim


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

    def write_claim_sidecar(self, task_path: Path, claim: TaskClaim) -> Path:
        sidecar = task_path.with_suffix(task_path.suffix + ".claim.json")
        sidecar.write_text(json.dumps(claim.to_dict(), indent=2), encoding="utf-8")
        return sidecar

    def read_claim_sidecar(self, task_path: Path) -> TaskClaim:
        sidecar = task_path.with_suffix(task_path.suffix + ".claim.json")
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
