from __future__ import annotations

from pathlib import Path

from agents.platinum.git_sync_manager import GitSyncManager
from agents.platinum.models import ConflictType


def test_preflight_blocks_forbidden_and_local_owned(monkeypatch, tmp_path):
    manager = GitSyncManager(tmp_path, node_id="cloud")
    monkeypatch.setattr(
        manager,
        "_changed_files",
        lambda: [Path(".env"), Path("Approved/item.md")],
    )

    result = manager.preflight()

    assert result.blocked is True
    assert any(path.endswith(".env") for path in result.forbidden)
    assert any("Approved" in path for path in result.local_owned)


def test_classify_conflict_paths(tmp_path):
    manager = GitSyncManager(tmp_path, node_id="cloud")

    assert manager._classify_conflict("Dashboard.md") is ConflictType.DASHBOARD
    assert manager._classify_conflict("Plans/plan.md") is ConflictType.PLAN
    assert manager._classify_conflict("In_Progress/cloud/task.md") is ConflictType.CLAIM
    assert manager._classify_conflict("Approved/item.md") is ConflictType.APPROVAL
    assert manager._classify_conflict("notes.md") is ConflictType.GENERIC
