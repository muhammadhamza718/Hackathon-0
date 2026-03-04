"""Unit tests for agents.inbox_scanner module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.inbox_scanner import (
    Priority,
    ScanResult,
    extract_priority,
    prioritize_inbox,
    scan_inbox,
)


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    (tmp_path / "Inbox").mkdir()
    return tmp_path


class TestPriorityEnum:
    """Verify Priority IntEnum ordering and parsing."""

    def test_natural_ordering(self):
        assert Priority.CRITICAL < Priority.HIGH < Priority.MEDIUM < Priority.LOW

    def test_from_string_valid(self):
        assert Priority.from_string("high") is Priority.HIGH

    def test_from_string_case_insensitive(self):
        assert Priority.from_string("LOW") is Priority.LOW

    def test_from_string_unknown_defaults_medium(self):
        assert Priority.from_string("unknown") is Priority.MEDIUM

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("critical", Priority.CRITICAL),
            ("high", Priority.HIGH),
            ("medium", Priority.MEDIUM),
            ("low", Priority.LOW),
        ],
    )
    def test_from_string_all_values(self, value: str, expected: Priority):
        assert Priority.from_string(value) is expected


class TestScanResult:
    """Verify the frozen ScanResult dataclass."""

    def test_is_urgent_critical(self, tmp_path: Path):
        result = ScanResult(path=tmp_path / "task.md", priority=Priority.CRITICAL)
        assert result.is_urgent is True

    def test_is_urgent_high(self, tmp_path: Path):
        result = ScanResult(path=tmp_path / "task.md", priority=Priority.HIGH)
        assert result.is_urgent is True

    def test_not_urgent_medium(self, tmp_path: Path):
        result = ScanResult(path=tmp_path / "task.md", priority=Priority.MEDIUM)
        assert result.is_urgent is False

    def test_frozen(self, tmp_path: Path):
        result = ScanResult(path=tmp_path / "task.md", priority=Priority.LOW)
        with pytest.raises(AttributeError):
            result.priority = Priority.HIGH  # type: ignore[misc]


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
        assert extract_priority("Priority: high\n") is Priority.HIGH

    def test_low_case_insensitive(self):
        assert extract_priority("priority: LOW") is Priority.LOW

    def test_default_medium(self):
        assert extract_priority("No priority here") is Priority.MEDIUM

    def test_critical(self):
        assert extract_priority("Priority: critical\n") is Priority.CRITICAL


class TestPrioritizeInbox:
    def test_sorts_by_priority(self, vault: Path):
        (vault / "Inbox" / "low.md").write_text("Priority: low\n")
        (vault / "Inbox" / "high.md").write_text("Priority: high\n")
        result = prioritize_inbox(vault)
        assert result[0].path.stem == "high"
        assert result[1].path.stem == "low"

    def test_critical_comes_first(self, vault: Path):
        (vault / "Inbox" / "med.md").write_text("Priority: medium\n")
        (vault / "Inbox" / "crit.md").write_text("Priority: critical\n")
        result = prioritize_inbox(vault)
        assert result[0].path.stem == "crit"
        assert result[0].priority is Priority.CRITICAL

    def test_returns_scan_results(self, vault: Path):
        (vault / "Inbox" / "task.md").write_text("Priority: high\n")
        result = prioritize_inbox(vault)
        assert isinstance(result[0], ScanResult)

    def test_empty(self, vault: Path):
        assert prioritize_inbox(vault) == []
