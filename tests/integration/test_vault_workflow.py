"""Integration test: full vault triage workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.dashboard_writer import write_dashboard
from agents.hitl_gate import HITLGate
from agents.vault_router import classify_task, mark_done, route_file


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    for d in ("Inbox", "Needs_Action", "Done", "Pending_Approval",
              "Approved", "Rejected", "Plans", "Logs"):
        (tmp_path / d).mkdir()
    return tmp_path


class TestSimpleTaskWorkflow:
    """Simple task: Inbox → Needs_Action → Done."""

    def test_full_lifecycle(self, vault: Path):
        # Create task in Inbox
        task = vault / "Inbox" / "fix-typo.md"
        task.write_text("# Fix Typo\n\nCorrect the spelling mistake.")

        # Classify
        content = task.read_text()
        assert classify_task(content) == "simple"

        # Route
        routed = route_file(task, vault)
        assert routed.parent.name == "Needs_Action"
        assert not task.exists()

        # Complete
        done = mark_done(routed, vault)
        assert done.parent.name == "Done"
        assert not routed.exists()

        # Dashboard
        dash = write_dashboard(vault)
        dashboard_content = dash.read_text()
        assert "| Done | 1 |" in dashboard_content


class TestComplexTaskWorkflow:
    """Complex task: Inbox → Pending_Approval → (human) → Approved."""

    def test_full_lifecycle(self, vault: Path):
        # Create complex task
        task = vault / "Inbox" / "send-report.md"
        task.write_text("# Send Report\n\nEmail the quarterly report to client.")

        # Classify
        assert classify_task(task.read_text()) == "complex"

        # Route to pending
        routed = route_file(task, vault)
        assert routed.parent.name == "Pending_Approval"

        # HITL gate check
        gate = HITLGate(vault)
        assert gate.check_decision("send-report.md") == "pending"

        # Simulate human approval (move file)
        approved_path = vault / "Approved" / "send-report.md"
        routed.rename(approved_path)

        assert gate.check_decision("send-report.md") == "approved"
