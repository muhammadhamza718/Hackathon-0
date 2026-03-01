"""Unit tests for agents.inbox_scanner module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.inbox_scanner import extract_priority, prioritize_inbox, scan_inbox


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    (tmp_path / "Inbox").mkdir()
    return tmp_path


class TestScanInbox:
    def test_empty_inbox(self, vault: Path):
        assert scan_inbox(vault) == []

    def test_finds_md_files(self, vault: Path):
        (vault / "Inbox" / "task.md").write_text("x")
        assert len(scan_inbox(vault)) == 1

    def test_no_inbox_dir(self, tmp_path: Path):
        assert scan_inbox(tmp_path) == []


class TestExtractPriority:
    def test_high(self):
        assert extract_priority("Priority: high\n") == "high"

    def test_low_case_insensitive(self):
        assert extract_priority("priority: LOW") == "low"

    def test_default_medium(self):
        assert extract_priority("No priority here") == "medium"


class TestPrioritizeInbox:
    def test_sorts_by_priority(self, vault: Path):
        (vault / "Inbox" / "low.md").write_text("Priority: low\n")
        (vault / "Inbox" / "high.md").write_text("Priority: high\n")
        result = prioritize_inbox(vault)
        assert result[0][0].stem == "high"
        assert result[1][0].stem == "low"

    def test_empty(self, vault: Path):
        assert prioritize_inbox(vault) == []
