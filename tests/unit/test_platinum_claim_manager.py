from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

from agents.constants import IN_PROGRESS_DIR, NEEDS_ACTION_DIR, UPDATES_DIR
from agents.platinum.claim_manager import ClaimManager
from agents.platinum.models import ClaimState, SyncResult, SyncState


def test_claim_task_moves_and_writes_sidecar(tmp_path):
    needs_action = tmp_path / NEEDS_ACTION_DIR
    needs_action.mkdir(parents=True, exist_ok=True)
    task = needs_action / "task-1.md"
    task.write_text("test", encoding="utf-8")

    mgr = ClaimManager(tmp_path, node_id="cloud")
    claim = mgr.claim_task(task)

    claimed_path = tmp_path / IN_PROGRESS_DIR / "cloud" / "task-1.md"
    assert claimed_path.exists()
    sidecar = claimed_path.with_suffix(".md.claim.json")
    assert sidecar.exists()
    assert claim.state is ClaimState.TENTATIVE


def test_confirm_and_release_claim(tmp_path):
    mgr = ClaimManager(tmp_path, node_id="local")
    claim = mgr.claim_task(_create_task(tmp_path, "task-2.md"))

    state = SyncState(
        node_id="local",
        sync_started_at=datetime.utcnow(),
        sync_finished_at=datetime.utcnow(),
        result=SyncResult.SUCCESS,
    )
    confirmed = mgr.confirm_claim(claim, state)
    assert confirmed.state is ClaimState.COMMITTED

    released = mgr.release_claim(confirmed, "completed")
    assert released.state is ClaimState.COMPLETED
    sidecar = Path(released.current_path).with_suffix(".md.claim.json")
    assert sidecar.exists()


def test_reconcile_claim_conflict_moves_loser(tmp_path):
    mgr = ClaimManager(tmp_path, node_id="local")
    local_task = _create_task(tmp_path, "task-local.md")
    remote_task = _create_task(tmp_path, "task-remote.md")

    local_claim = mgr.claim_task(local_task)
    remote_mgr = ClaimManager(tmp_path, node_id="cloud")
    remote_claim = remote_mgr.claim_task(remote_task)

    remote_claim = replace(
        remote_claim,
        claimed_at=datetime.utcnow() + timedelta(seconds=10),
        lease_expires_at=datetime.utcnow() + timedelta(seconds=20),
    )

    record = mgr.reconcile_claim_conflict(local_claim, remote_claim)
    assert record.conflict_type.value == "claim"

    conflicts_dir = (
        tmp_path / UPDATES_DIR / "conflicts" / "claims" / remote_claim.owner_node
    )
    assert conflicts_dir.exists()
    moved_task = conflicts_dir / Path(remote_claim.current_path).name
    assert moved_task.exists()
    sidecar = moved_task.with_suffix(moved_task.suffix + ".claim.json")
    assert sidecar.exists()


def _create_task(tmp_path, name: str):
    needs_action = tmp_path / NEEDS_ACTION_DIR
    needs_action.mkdir(parents=True, exist_ok=True)
    path = needs_action / name
    path.write_text("test", encoding="utf-8")
    return path
