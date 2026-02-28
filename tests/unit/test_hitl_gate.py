"""Unit tests for agents.hitl_gate module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.hitl_gate import HITLGate


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    for d in ("Pending_Approval", "Approved", "Rejected"):
        (tmp_path / d).mkdir()
    return tmp_path


@pytest.fixture
def gate(vault: Path) -> HITLGate:
    return HITLGate(vault)


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
        assert gate.check_decision("task.md") == "pending"

    def test_approved(self, vault: Path, gate: HITLGate):
        (vault / "Approved" / "task.md").write_text("yes")
        assert gate.check_decision("task.md") == "approved"

    def test_rejected(self, vault: Path, gate: HITLGate):
        (vault / "Rejected" / "task.md").write_text("no")
        assert gate.check_decision("task.md") == "rejected"
