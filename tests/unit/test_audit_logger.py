"""Unit tests for agents.audit_logger module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.audit_logger import append_log, read_log


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
