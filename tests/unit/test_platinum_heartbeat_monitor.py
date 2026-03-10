from __future__ import annotations

import json
from datetime import datetime, timedelta

from agents.constants import INBOX_DIR, NEEDS_ACTION_DIR, UPDATES_HEARTBEATS_DIR
from agents.platinum.heartbeat_monitor import HeartbeatMonitor
from agents.platinum.models import NodeRole, NodeStatus


def test_publish_writes_heartbeat_and_counts(tmp_path):
    inbox = tmp_path / INBOX_DIR
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "a.md").write_text("a", encoding="utf-8")
    (inbox / "b.md").write_text("b", encoding="utf-8")

    needs_action = tmp_path / NEEDS_ACTION_DIR
    needs_action.mkdir(parents=True, exist_ok=True)
    (needs_action / "task.md").write_text("task", encoding="utf-8")

    monitor = HeartbeatMonitor(tmp_path, node_id="cloud", role=NodeRole.CLOUD)
    heartbeat = monitor.publish()

    path = tmp_path / UPDATES_HEARTBEATS_DIR / "cloud.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["node_id"] == heartbeat.node_id
    assert data["queue_counts"]["inbox"] == 2
    assert data["queue_counts"]["needs_action"] == 1


def test_evaluate_status_offline_when_stale(tmp_path):
    monitor = HeartbeatMonitor(tmp_path, node_id="cloud", role=NodeRole.CLOUD)
    monitor.publish()

    path = tmp_path / UPDATES_HEARTBEATS_DIR / "cloud.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["last_seen_at"] = (
        datetime.utcnow() - timedelta(seconds=1000)
    ).isoformat() + "Z"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    status, age = monitor.evaluate_status("cloud", warn_seconds=300, stale_seconds=900)
    assert status is NodeStatus.OFFLINE
    assert age is not None
    assert monitor.should_enter_single_node_mode("cloud", stale_seconds=900)
