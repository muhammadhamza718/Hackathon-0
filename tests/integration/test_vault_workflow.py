"""Integration test: full vault triage workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.dashboard_writer import snapshot_vault, write_dashboard
from agents.hitl_gate import Decision, HITLGate
from agents.vault_router import TaskClassification, classify_task, mark_done, route_file


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
        assert classify_task(content) is TaskClassification.SIMPLE

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
        assert classify_task(task.read_text()) is TaskClassification.COMPLEX

        # Route to pending
        routed = route_file(task, vault)
        assert routed.parent.name == "Pending_Approval"

        # HITL gate check
        gate = HITLGate(vault)
        decision = gate.check_decision("send-report.md")
        assert decision is Decision.PENDING
        assert decision.is_final is False

        # Simulate human approval (move file)
        approved_path = vault / "Approved" / "send-report.md"
        routed.rename(approved_path)

        decision = gate.check_decision("send-report.md")
        assert decision is Decision.APPROVED
        assert decision.is_final is True


class TestVaultStatusIntegration:
    """Verify snapshot_vault reflects actual vault state changes."""

    def test_snapshot_tracks_routing(self, vault: Path):
        # Start with a task in Inbox
        task = vault / "Inbox" / "task.md"
        task.write_text("# Simple task\n\nDo it.")

        before = snapshot_vault(vault)
        assert before.inbox == 1
        assert before.has_actionable_items is True

        # Route it
        route_file(task, vault)
        after = snapshot_vault(vault)
        assert after.inbox == 0
        assert after.needs_action == 1
        assert after.has_actionable_items is True

        # Mark done
        routed = list((vault / "Needs_Action").glob("*.md"))[0]
        mark_done(routed, vault)
        final = snapshot_vault(vault)
        assert final.needs_action == 0
        assert final.done == 1
        assert final.has_actionable_items is False
