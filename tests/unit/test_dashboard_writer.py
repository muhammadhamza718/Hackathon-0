"""Unit tests for agents.dashboard_writer module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.dashboard_writer import (
    VaultStatus,
    count_files,
    generate_dashboard,
    snapshot_vault,
    write_dashboard,
)


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    for d in ("Inbox", "Needs_Action", "Done", "Pending_Approval",
              "Approved", "Rejected", "Plans"):
        (tmp_path / d).mkdir()
    return tmp_path


class TestCountFiles:
    def test_empty_dir(self, vault: Path):
        assert count_files(vault / "Inbox") == 0

    def test_with_files(self, vault: Path):
        (vault / "Inbox" / "a.md").write_text("a")
        (vault / "Inbox" / "b.md").write_text("b")
        assert count_files(vault / "Inbox") == 2

    def test_nonexistent_dir(self, tmp_path: Path):
        assert count_files(tmp_path / "nope") == 0

    def test_ignores_non_md(self, vault: Path):
        (vault / "Inbox" / "a.txt").write_text("a")
        assert count_files(vault / "Inbox") == 0


class TestGenerateDashboard:
    def test_contains_header(self, vault: Path):
        md = generate_dashboard(vault)
        assert "# Dashboard" in md

    def test_contains_table(self, vault: Path):
        md = generate_dashboard(vault)
        assert "| Folder | Count |" in md

    def test_shows_inbox_count(self, vault: Path):
        (vault / "Inbox" / "task.md").write_text("x")
        md = generate_dashboard(vault)
        assert "| Inbox | 1 |" in md

    def test_includes_distributed_status_section(self, vault: Path):
        md = generate_dashboard(vault)
        assert "## Distributed Status" in md
        assert "## Distributed Alerts" in md


class TestWriteDashboard:
    def test_creates_file(self, vault: Path):
        path = write_dashboard(vault)
        assert path.exists()
        assert path.name == "Dashboard.md"

    def test_content_is_markdown(self, vault: Path):
        path = write_dashboard(vault)
        content = path.read_text()
        assert content.startswith("# Dashboard")


class TestVaultStatus:
    """Verify frozen VaultStatus dataclass."""

    def test_total_sums_all_folders(self):
        status = VaultStatus(
            inbox=1, needs_action=2, pending_approval=3,
            approved=4, rejected=0, done=5, plans=1, logs=2,
        )
        assert status.total == 18

    def test_total_empty(self):
        status = VaultStatus(
            inbox=0, needs_action=0, pending_approval=0,
            approved=0, rejected=0, done=0, plans=0, logs=0,
        )
        assert status.total == 0

    def test_has_actionable_items_inbox(self):
        status = VaultStatus(
            inbox=1, needs_action=0, pending_approval=0,
            approved=0, rejected=0, done=0, plans=0, logs=0,
        )
        assert status.has_actionable_items is True

    def test_has_actionable_items_needs_action(self):
        status = VaultStatus(
            inbox=0, needs_action=3, pending_approval=0,
            approved=0, rejected=0, done=0, plans=0, logs=0,
        )
        assert status.has_actionable_items is True

    def test_no_actionable_items(self):
        status = VaultStatus(
            inbox=0, needs_action=0, pending_approval=5,
            approved=0, rejected=0, done=0, plans=0, logs=0,
        )
        assert status.has_actionable_items is False

    def test_frozen(self):
        status = VaultStatus(
            inbox=0, needs_action=0, pending_approval=0,
            approved=0, rejected=0, done=0, plans=0, logs=0,
        )
        with pytest.raises(AttributeError):
            status.inbox = 5  # type: ignore[misc]


class TestSnapshotVault:
    def test_captures_counts(self, vault: Path):
        (vault / "Inbox" / "a.md").write_text("x")
        (vault / "Done" / "b.md").write_text("y")
        status = snapshot_vault(vault)
        assert status.inbox == 1
        assert status.done == 1
        assert status.total == 2

    def test_empty_vault(self, vault: Path):
        status = snapshot_vault(vault)
        assert status.total == 0
