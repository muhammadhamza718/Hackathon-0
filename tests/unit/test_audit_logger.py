"""Unit tests for agents.audit_logger module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.audit_logger import AuditEntry, append_log, read_log


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    (tmp_path / "Logs").mkdir()
    return tmp_path


class TestAppendLog:
    def test_creates_log_file(self, vault: Path):
        path = append_log(vault, "route", "Moved task.md to Needs_Action")
        assert path.exists()

    def test_contains_action(self, vault: Path):
        append_log(vault, "approve", "Approved send-report.md")
        content = read_log(vault)
        assert "**approve**" in content

    def test_contains_tier(self, vault: Path):
        append_log(vault, "route", "test", tier="silver")
        content = read_log(vault)
        assert "[silver]" in content

    def test_multiple_entries(self, vault: Path):
        append_log(vault, "route", "first")
        append_log(vault, "approve", "second")
        content = read_log(vault)
        assert "first" in content
        assert "second" in content

    def test_has_header(self, vault: Path):
        append_log(vault, "test", "entry")
        content = read_log(vault)
        assert "# Audit Log" in content


class TestReadLog:
    def test_empty_when_no_log(self, vault: Path):
        assert read_log(vault) == ""

    def test_reads_specific_date(self, vault: Path):
        assert read_log(vault, date="2020-01-01") == ""


class TestAuditEntry:
    """Verify frozen AuditEntry dataclass and factory."""

    def test_format_line_contains_all_fields(self):
        entry = AuditEntry(
            timestamp="2026-03-05T10:00:00",
            tier="silver",
            action="approve",
            detail="Approved task.md",
        )
        line = entry.format_line()
        assert "[2026-03-05T10:00:00]" in line
        assert "[silver]" in line
        assert "**approve**" in line
        assert "Approved task.md" in line

    def test_format_line_ends_with_newline(self):
        entry = AuditEntry(
            timestamp="2026-01-01T00:00:00",
            tier="bronze",
            action="route",
            detail="test",
        )
        assert entry.format_line().endswith("\n")

    def test_now_factory_returns_entry(self):
        entry = AuditEntry.now(action="scan", detail="Scanned inbox")
        assert entry.action == "scan"
        assert entry.tier == "bronze"
        assert len(entry.timestamp) == 19  # YYYY-MM-DDTHH:MM:SS

    def test_now_factory_custom_tier(self):
        entry = AuditEntry.now(action="deploy", detail="test", tier="gold")
        assert entry.tier == "gold"

    def test_frozen(self):
        entry = AuditEntry.now(action="test", detail="x")
        with pytest.raises(AttributeError):
            entry.action = "mutated"  # type: ignore[misc]
