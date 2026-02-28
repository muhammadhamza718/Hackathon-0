"""Unit tests for agents.dashboard_writer module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.dashboard_writer import count_files, generate_dashboard, write_dashboard


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


class TestWriteDashboard:
    def test_creates_file(self, vault: Path):
        path = write_dashboard(vault)
        assert path.exists()
        assert path.name == "Dashboard.md"

    def test_content_is_markdown(self, vault: Path):
        path = write_dashboard(vault)
        content = path.read_text()
        assert content.startswith("# Dashboard")
