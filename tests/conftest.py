"""Shared fixtures for all test directories."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def full_vault(tmp_path: Path) -> Path:
    """Create a complete vault structure with all required directories."""
    dirs = [
        "Inbox", "Needs_Action", "Done",
        "Pending_Approval", "Approved", "Rejected",
        "Plans", "Logs",
    ]
    for d in dirs:
        (tmp_path / d).mkdir()
    return tmp_path


@pytest.fixture
def populated_vault(full_vault: Path) -> Path:
    """Vault with sample files in multiple directories."""
    (full_vault / "Inbox" / "new-task.md").write_text(
        "# New Task\n\nPriority: high\n\nDo something."
    )
    (full_vault / "Needs_Action" / "pending-task.md").write_text(
        "# Pending Task\n\nWaiting for execution."
    )
    (full_vault / "Done" / "old-task.md").write_text(
        "# Old Task\n\nCompleted."
    )
    return full_vault
