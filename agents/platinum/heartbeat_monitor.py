"""Heartbeat publishing and staleness checks for Platinum nodes."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from agents.constants import (
    INBOX_DIR,
    NEEDS_ACTION_DIR,
    PENDING_APPROVAL_DIR,
    APPROVED_DIR,
    REJECTED_DIR,
    DONE_DIR,
    PLANS_DIR,
    UPDATES_HEARTBEATS_DIR,
)
from agents.platinum.models import NodeHeartbeat, NodeRole, NodeStatus


class HeartbeatMonitor:
    def __init__(self, vault_root: Path, node_id: str, role: NodeRole):
        self.vault_root = vault_root
        self.node_id = node_id
        self.role = role

    def _queue_counts(self) -> dict[str, int]:
        def count(dir_name: str) -> int:
            path = self.vault_root / dir_name
            if not path.exists():
                return 0
            return len(list(path.glob("*.md")))

        return {
            "inbox": count(INBOX_DIR),
            "needs_action": count(NEEDS_ACTION_DIR),
            "pending_approval": count(PENDING_APPROVAL_DIR),
            "approved": count(APPROVED_DIR),
            "rejected": count(REJECTED_DIR),
            "done": count(DONE_DIR),
            "plans": count(PLANS_DIR),
        }

    def publish(self, last_sync_at: datetime | None = None, odoo_status: str | None = None) -> NodeHeartbeat:
        now = datetime.utcnow()
        heartbeat = NodeHeartbeat(
            node_id=self.node_id,
            role=self.role,
            status=NodeStatus.HEALTHY,
            last_seen_at=now,
            last_sync_at=last_sync_at,
            queue_counts=self._queue_counts(),
            odoo_status=odoo_status,
            notes=None,
        )
        self._write_heartbeat(heartbeat)
        return heartbeat

    def _write_heartbeat(self, heartbeat: NodeHeartbeat) -> Path:
        updates_dir = self.vault_root / UPDATES_HEARTBEATS_DIR
        updates_dir.mkdir(parents=True, exist_ok=True)
        path = updates_dir / f"{self.node_id}.json"
        path.write_text(json.dumps(heartbeat.to_dict(), indent=2), encoding="utf-8")
        return path

    def read(self, node_id: str) -> dict[str, Any] | None:
        path = self.vault_root / UPDATES_HEARTBEATS_DIR / f"{node_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def is_stale(self, node_id: str, stale_seconds: int) -> bool:
        data = self.read(node_id)
        if not data:
            return True
        last_seen = datetime.fromisoformat(data["last_seen_at"].replace("Z", ""))
        return datetime.utcnow() - last_seen > timedelta(seconds=stale_seconds)
