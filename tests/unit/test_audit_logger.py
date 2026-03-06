"""Unit tests for agents.audit_logger module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.audit_logger import AuditEntry, append_log, parse_log_entries, read_log


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


class TestParseLogEntries:
    """Verify structured parsing of audit log content."""

    def test_parses_single_entry(self):
        content = "- [2026-03-06T10:00:00] [bronze] **route**: Moved task.md\n"
        entries = parse_log_entries(content)
        assert len(entries) == 1
        assert entries[0].action == "route"
        assert entries[0].tier == "bronze"
        assert entries[0].detail == "Moved task.md"

    def test_parses_multiple_entries(self):
        content = (
            "# Audit Log\n\n"
            "- [2026-03-06T10:00:00] [silver] **approve**: Approved task.md\n"
            "- [2026-03-06T10:01:00] [silver] **route**: Routed file.md\n"
        )
        entries = parse_log_entries(content)
        assert len(entries) == 2
        assert entries[0].action == "approve"
        assert entries[1].action == "route"

    def test_empty_content(self):
        assert parse_log_entries("") == []

    def test_no_matching_lines(self):
        assert parse_log_entries("# Just a header\n\nPlain text.") == []

    def test_roundtrip_format_parse(self):
        original = AuditEntry(
            timestamp="2026-03-06T12:30:00",
            tier="gold",
            action="deploy",
            detail="Deployed v1",
        )
        line = original.format_line()
        parsed = parse_log_entries(line)
        assert len(parsed) == 1
        assert parsed[0] == original
