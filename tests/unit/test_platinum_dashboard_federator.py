from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from agents.constants import IN_PROGRESS_DIR, UPDATES_HEARTBEATS_DIR, UPDATES_SYNC_DIR
from agents.platinum.dashboard_federator import federate_status
from agents.platinum.models import (
    ClaimState,
    NodeHeartbeat,
    NodeRole,
    NodeStatus,
    SyncResult,
    SyncState,
    TaskClaim,
)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_federate_status_collects_alerts_and_claims(tmp_path):
    now = datetime.utcnow()

    cloud_heartbeat = NodeHeartbeat(
        node_id="cloud",
        role=NodeRole.CLOUD,
        status=NodeStatus.HEALTHY,
        last_seen_at=now - timedelta(seconds=400),
    )
    local_heartbeat = NodeHeartbeat(
        node_id="local",
        role=NodeRole.LOCAL,
        status=NodeStatus.HEALTHY,
        last_seen_at=now,
    )

    _write_json(
        tmp_path / UPDATES_HEARTBEATS_DIR / "cloud.json",
        cloud_heartbeat.to_dict(),
    )
    _write_json(
        tmp_path / UPDATES_HEARTBEATS_DIR / "local.json",
        local_heartbeat.to_dict(),
    )

    sync_state = SyncState(
        node_id="cloud",
        sync_started_at=now - timedelta(seconds=700),
        sync_finished_at=now - timedelta(seconds=600),
        result=SyncResult.SUCCESS,
    )
    _write_json(tmp_path / UPDATES_SYNC_DIR / "cloud.json", sync_state.to_dict())

    claim = TaskClaim(
        task_id="task",
        owner_node="cloud",
        claim_nonce="abc",
        claimed_at=now - timedelta(seconds=30),
        lease_expires_at=now + timedelta(seconds=300),
        state=ClaimState.COMMITTED,
        source_path="Needs_Action/task.md",
        current_path=str(tmp_path / IN_PROGRESS_DIR / "cloud" / "task.md"),
        last_heartbeat_at=now,
    )
    claim_dir = tmp_path / IN_PROGRESS_DIR / "cloud"
    claim_dir.mkdir(parents=True, exist_ok=True)
    (claim_dir / "task.md").write_text("task", encoding="utf-8")
    _write_json(
        claim_dir / "task.md.claim.json",
        claim.to_dict(),
    )

    status = federate_status(
        tmp_path,
        warn_seconds=300,
        stale_seconds=900,
        sync_warn_seconds=300,
    )

    assert status.node_health["cloud"]["status"] == NodeStatus.DEGRADED.value
    assert any("cloud heartbeat" in alert for alert in status.alerts)
    assert any("cloud sync lag" in alert for alert in status.alerts)
    assert len(status.active_claims) == 1
    assert status.active_claims[0].task_id == "task"
