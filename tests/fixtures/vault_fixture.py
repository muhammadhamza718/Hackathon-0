"""Shared vault fixtures for tests."""

from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture
def vault_root(tmp_path: Path) -> Path:
    """Create a minimal Obsidian vault structure for testing."""
    dirs = [
        "Inbox",
        "Needs_Action",
        "Done",
        "Pending_Approval",
        "Approved",
        "Rejected",
        "Plans",
        "Logs",
    ]
    for d in dirs:
        (tmp_path / d).mkdir()
    return tmp_path


@pytest.fixture
def inbox_with_files(vault_root: Path) -> Path:
    """Vault with sample files in Inbox."""
    inbox = vault_root / "Inbox"
    (inbox / "task-001.md").write_text("# Task 001\n\nDo something important.\n")
    (inbox / "task-002.md").write_text("# Task 002\n\nReview the report.\n")
    return vault_root


@pytest.fixture
def plan_file(vault_root: Path) -> Path:
    """Create a sample Plan file in the Plans directory."""
    content = """---
task_id: PLAN-2026-001
status: active
priority: high
created_date: 2026-02-27
---
# Objective
Test the silver reasoning agent.

## Roadmap
- [x] Step 1: Initialize
- [ ] Step 2: Execute ✋
- [ ] Step 3: Complete
"""
    path = vault_root / "Plans" / "PLAN-2026-001.md"
    path.write_text(content)
    return path
