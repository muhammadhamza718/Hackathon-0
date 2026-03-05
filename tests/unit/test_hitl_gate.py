"""Unit tests for agents.hitl_gate module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.hitl_gate import Decision, HITLGate


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    for d in ("Pending_Approval", "Approved", "Rejected"):
        (tmp_path / d).mkdir()
    return tmp_path


@pytest.fixture
def gate(vault: Path) -> HITLGate:
    return HITLGate(vault)


class TestDecisionEnum:
    """Verify Decision enum values and properties."""

    def test_approved_value(self):
        assert Decision.APPROVED.value == "approved"

    def test_rejected_value(self):
        assert Decision.REJECTED.value == "rejected"

    def test_pending_value(self):
        assert Decision.PENDING.value == "pending"

    @pytest.mark.parametrize(
        "decision,expected",
        [
            (Decision.APPROVED, True),
            (Decision.REJECTED, True),
            (Decision.PENDING, False),
        ],
    )
    def test_is_final(self, decision: Decision, expected: bool):
        assert decision.is_final is expected


class TestSubmitForApproval:
    def test_moves_file(self, vault: Path, gate: HITLGate):
        f = vault / "task.md"
        f.write_text("approve me")
        dest = gate.submit_for_approval(f)
        assert dest.parent.name == "Pending_Approval"
        assert not f.exists()

    def test_missing_file_raises(self, gate: HITLGate, vault: Path):
        with pytest.raises(FileNotFoundError):
            gate.submit_for_approval(vault / "nope.md")


class TestGetPending:
    def test_empty(self, gate: HITLGate):
        assert gate.get_pending() == []

    def test_returns_pending(self, vault: Path, gate: HITLGate):
        (vault / "Pending_Approval" / "a.md").write_text("x")
        assert len(gate.get_pending()) == 1


class TestCheckDecision:
    def test_pending(self, gate: HITLGate):
        assert gate.check_decision("task.md") is Decision.PENDING

    def test_approved(self, vault: Path, gate: HITLGate):
        (vault / "Approved" / "task.md").write_text("yes")
        assert gate.check_decision("task.md") is Decision.APPROVED

    def test_rejected(self, vault: Path, gate: HITLGate):
        (vault / "Rejected" / "task.md").write_text("no")
        assert gate.check_decision("task.md") is Decision.REJECTED

    def test_approved_is_final(self, vault: Path, gate: HITLGate):
        (vault / "Approved" / "task.md").write_text("yes")
        assert gate.check_decision("task.md").is_final is True

    def test_pending_not_final(self, gate: HITLGate):
        assert gate.check_decision("task.md").is_final is False


class TestPendingCount:
    def test_zero_when_empty(self, gate: HITLGate):
        assert gate.pending_count == 0

    def test_counts_md_files(self, vault: Path, gate: HITLGate):
        (vault / "Pending_Approval" / "a.md").write_text("x")
        (vault / "Pending_Approval" / "b.md").write_text("y")
        assert gate.pending_count == 2
