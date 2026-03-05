"""Shared fixtures for all test directories."""

from __future__ import annotations

from pathlib import Path

import pytest

VAULT_DIRS = (
    "Inbox",
    "Needs_Action",
    "Done",
    "Pending_Approval",
    "Approved",
    "Rejected",
    "Plans",
    "Logs",
)
"""Tuple of all required vault directory names."""


@pytest.fixture
def full_vault(tmp_path: Path) -> Path:
    """Create a complete vault structure with all required directories."""
    for d in VAULT_DIRS:
        (tmp_path / d).mkdir()
    return tmp_path


@pytest.fixture
def populated_vault(full_vault: Path) -> Path:
    """Vault with sample files in multiple directories."""
    (full_vault / "Inbox" / "new-task.md").write_text(
        "---\ntitle: New Task\npriority: high\nstatus: pending\n---\n"
        "# New Task\n\nPriority: high\n\nDo something."
    )
    (full_vault / "Inbox" / "low-task.md").write_text(
        "---\ntitle: Low Task\npriority: low\nstatus: pending\n---\n"
        "# Low Task\n\nPriority: low\n\nMinor update."
    )
    (full_vault / "Needs_Action" / "pending-task.md").write_text(
        "# Pending Task\n\nWaiting for execution."
    )
    (full_vault / "Done" / "old-task.md").write_text(
        "# Old Task\n\nCompleted."
    )
    (full_vault / "Plans" / "PLAN-2026-001.md").write_text(
        "---\ntask_id: PLAN-2026-001\nstatus: active\npriority: high\n---\n"
        "# Objective\nTest plan.\n\n## Roadmap\n- [x] Step 1\n- [ ] Step 2\n"
    )
    return full_vault
