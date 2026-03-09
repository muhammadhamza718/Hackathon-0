"""Data models for Platinum distributed coordination."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


def _utc_now() -> datetime:
    return datetime.utcnow()


class NodeRole(str, Enum):
    CLOUD = "cloud"
    LOCAL = "local"
    RECOVERING = "recovering"


class NodeStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    RECOVERING = "recovering"


class SyncResult(str, Enum):
    SUCCESS = "success"
    CONFLICT = "conflict"
    BLOCKED = "blocked"
    FAILED = "failed"


class ClaimState(str, Enum):
    TENTATIVE = "tentative"
    COMMITTED = "committed"
    ACTIVE = "active"
    RELEASED = "released"
    COMPLETED = "completed"
    STALE = "stale"
    TAKEN_OVER = "taken_over"


class ConflictType(str, Enum):
    DASHBOARD = "dashboard"
    PLAN = "plan"
    CLAIM = "claim"
    APPROVAL = "approval"
    GENERIC = "generic_markdown"


@dataclass(frozen=True)
class NodeHeartbeat:
    node_id: str
    role: NodeRole
    status: NodeStatus
    last_seen_at: datetime
    last_sync_at: datetime | None = None
    queue_counts: dict[str, int] = field(default_factory=dict)
    odoo_status: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "role": self.role.value,
            "status": self.status.value,
            "last_seen_at": self.last_seen_at.isoformat() + "Z",
            "last_sync_at": self.last_sync_at.isoformat() + "Z"
            if self.last_sync_at
            else None,
            "queue_counts": self.queue_counts,
            "odoo_status": self.odoo_status,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class TaskClaim:
    task_id: str
    owner_node: str
    claim_nonce: str
    claimed_at: datetime
    lease_expires_at: datetime
    state: ClaimState
    source_path: str
    current_path: str
    last_heartbeat_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "owner_node": self.owner_node,
            "claim_nonce": self.claim_nonce,
            "claimed_at": self.claimed_at.isoformat() + "Z",
            "lease_expires_at": self.lease_expires_at.isoformat() + "Z",
            "state": self.state.value,
            "source_path": self.source_path,
            "current_path": self.current_path,
            "last_heartbeat_at": self.last_heartbeat_at.isoformat() + "Z"
            if self.last_heartbeat_at
            else None,
        }


@dataclass(frozen=True)
class SyncState:
    node_id: str
    sync_started_at: datetime
    sync_finished_at: datetime | None
    result: SyncResult
    ahead_count: int = 0
    behind_count: int = 0
    conflicted_files: list[str] = field(default_factory=list)
    excluded_paths_detected: list[str] = field(default_factory=list)
    latency_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "sync_started_at": self.sync_started_at.isoformat() + "Z",
            "sync_finished_at": self.sync_finished_at.isoformat() + "Z"
            if self.sync_finished_at
            else None,
            "result": self.result.value,
            "ahead_count": self.ahead_count,
            "behind_count": self.behind_count,
            "conflicted_files": self.conflicted_files,
            "excluded_paths_detected": self.excluded_paths_detected,
            "latency_seconds": self.latency_seconds,
        }


@dataclass(frozen=True)
class ConflictRecord:
    conflict_id: str
    file_path: str
    conflict_type: ConflictType
    winning_node: str
    losing_node: str | None
    resolution_state: str
    recorded_at: datetime = field(default_factory=_utc_now)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "file_path": self.file_path,
            "conflict_type": self.conflict_type.value,
            "winning_node": self.winning_node,
            "losing_node": self.losing_node,
            "resolution_state": self.resolution_state,
            "recorded_at": self.recorded_at.isoformat() + "Z",
            "notes": self.notes,
        }
