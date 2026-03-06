"""Unit tests for agents.gold.audit_gold module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.gold.audit_gold import append_gold_log, read_gold_log
from agents.gold.models import GoldAuditEntry


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    (tmp_path / "Logs").mkdir()
    return tmp_path


class TestGoldAuditEntry:
    def test_frozen(self):
        entry = GoldAuditEntry.now(action="triage", rationale="test")
        with pytest.raises(AttributeError):
            entry.action = "mutated"  # type: ignore[misc]

    def test_now_factory(self):
        entry = GoldAuditEntry.now(
            action="odoo_read", rationale="Plan#1", iteration=3, duration_ms=42
        )
        assert entry.action == "odoo_read"
        assert entry.rationale == "Plan#1"
        assert entry.tier == "gold"
        assert entry.iteration == 3
        assert entry.duration_ms == 42

    def test_to_dict_roundtrip(self):
        entry = GoldAuditEntry.now(
            action="social_draft",
            source_file="Pending_Approval/post.md",
            details="Draft X post",
            rationale="Campaign Q1",
        )
        d = entry.to_dict()
        assert d["action"] == "social_draft"
        assert d["rationale"] == "Campaign Q1"
        assert d["tier"] == "gold"
        assert "timestamp" in d

    def test_default_values(self):
        entry = GoldAuditEntry.now(action="triage", rationale="test")
        assert entry.iteration == 0
        assert entry.duration_ms == 0
        assert entry.result == "success"
        assert entry.source_file == ""


class TestAppendGoldLog:
    def test_creates_json_log(self, vault: Path):
        append_gold_log(vault, action="triage", rationale="Plan step 1")
        logs = list((vault / "Logs").glob("*.json"))
        assert len(logs) == 1

    def test_json_format(self, vault: Path):
        append_gold_log(vault, action="triage", rationale="Plan step 1")
        log_file = list((vault / "Logs").glob("*.json"))[0]
        data = json.loads(log_file.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["action"] == "triage"
        assert data[0]["rationale"] == "Plan step 1"

    def test_multiple_entries_append(self, vault: Path):
        append_gold_log(vault, action="triage", rationale="step 1")
        append_gold_log(vault, action="complete", rationale="step 2")
        log_file = list((vault / "Logs").glob("*.json"))[0]
        data = json.loads(log_file.read_text(encoding="utf-8"))
        assert len(data) == 2

    def test_empty_rationale_raises(self, vault: Path):
        with pytest.raises(ValueError, match="rationale"):
            append_gold_log(vault, action="triage", rationale="")

    def test_returns_entry(self, vault: Path):
        entry = append_gold_log(vault, action="move", rationale="cleanup")
        assert isinstance(entry, GoldAuditEntry)
        assert entry.action == "move"

    def test_custom_fields(self, vault: Path):
        entry = append_gold_log(
            vault,
            action="odoo_read",
            source_file="invoices.csv",
            details="Read 42 invoices",
            result="success",
            rationale="Revenue check",
            iteration=5,
            duration_ms=123,
        )
        assert entry.iteration == 5
        assert entry.duration_ms == 123


class TestReadGoldLog:
    def test_empty_when_no_log(self, vault: Path):
        result = read_gold_log(vault)
        assert result == []

    def test_reads_entries(self, vault: Path):
        append_gold_log(vault, action="triage", rationale="test")
        entries = read_gold_log(vault)
        assert len(entries) == 1

    def test_reads_specific_date(self, vault: Path):
        result = read_gold_log(vault, date="2020-01-01")
        assert result == []

    def test_handles_corrupt_json(self, vault: Path):
        log_dir = vault / "Logs"
        (log_dir / "2026-03-06.json").write_text("not json", encoding="utf-8")
        result = read_gold_log(vault, date="2026-03-06")
        assert result == []
