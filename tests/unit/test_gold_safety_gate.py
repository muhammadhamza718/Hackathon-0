"""Unit tests for agents.gold.safety_gate module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.gold.safety_gate import GoldSafetyGate
from agents.hitl_gate import Decision


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    for d in ("Pending_Approval", "Approved", "Rejected"):
        (tmp_path / d).mkdir()
    return tmp_path


@pytest.fixture
def gate(vault: Path) -> GoldSafetyGate:
    return GoldSafetyGate(vault)


class TestSocialPostDetection:
    def test_social_draft_detected(self):
        assert GoldSafetyGate.is_social_post("social_draft") is True

    def test_social_post_detected(self):
        assert GoldSafetyGate.is_social_post("social_post") is True

    def test_non_social_not_detected(self):
        assert GoldSafetyGate.is_social_post("odoo_read") is False


class TestPaymentThreshold:
    def test_above_threshold(self, gate: GoldSafetyGate):
        assert gate.exceeds_payment_threshold(150.0) is True

    def test_at_threshold(self, gate: GoldSafetyGate):
        assert gate.exceeds_payment_threshold(100.0) is False

    def test_below_threshold(self, gate: GoldSafetyGate):
        assert gate.exceeds_payment_threshold(50.0) is False

    def test_custom_threshold(self, vault: Path):
        gate = GoldSafetyGate(vault, payment_threshold=50.0)
        assert gate.exceeds_payment_threshold(75.0) is True
        assert gate.exceeds_payment_threshold(25.0) is False


class TestOdooWriteDetection:
    def test_write_draft_detected(self):
        assert GoldSafetyGate.is_odoo_write("odoo_write_draft") is True

    def test_read_not_detected(self):
        assert GoldSafetyGate.is_odoo_write("odoo_read") is False


class TestRequiresApproval:
    def test_social_requires_approval(self, gate: GoldSafetyGate):
        assert gate.requires_approval("social_draft") is True

    def test_odoo_write_requires_approval(self, gate: GoldSafetyGate):
        assert gate.requires_approval("odoo_write_draft") is True

    def test_high_payment_requires_approval(self, gate: GoldSafetyGate):
        assert gate.requires_approval("payment", amount=200.0) is True

    def test_low_payment_no_approval(self, gate: GoldSafetyGate):
        assert gate.requires_approval("payment", amount=50.0) is False

    def test_read_no_approval(self, gate: GoldSafetyGate):
        assert gate.requires_approval("odoo_read") is False


class TestApprovalFile:
    def test_creates_file(self, gate: GoldSafetyGate, vault: Path):
        path = gate.create_approval_file(
            action_type="social_draft",
            content="Post about product launch",
            rationale="Marketing campaign Q1",
            platform="X",
        )
        assert path.exists()
        assert path.parent.name == "Pending_Approval"

    def test_file_contains_frontmatter(self, gate: GoldSafetyGate):
        path = gate.create_approval_file(
            action_type="odoo_write_draft",
            content="Create invoice #42",
            rationale="Client billing",
            amount=500.0,
        )
        content = path.read_text(encoding="utf-8")
        assert "type: odoo_write_draft" in content
        assert "amount: 500.00" in content
        assert "rationale: Client billing" in content

    def test_file_contains_content(self, gate: GoldSafetyGate):
        path = gate.create_approval_file(
            action_type="social_draft",
            content="Hello world",
            rationale="test",
        )
        content = path.read_text(encoding="utf-8")
        assert "Hello world" in content


class TestCheckDecision:
    def test_pending_default(self, gate: GoldSafetyGate):
        assert gate.check_decision("unknown.md") is Decision.PENDING

    def test_approved(self, gate: GoldSafetyGate, vault: Path):
        (vault / "Approved" / "task.md").write_text("yes")
        assert gate.check_decision("task.md") is Decision.APPROVED

    def test_is_approved_shorthand(self, gate: GoldSafetyGate, vault: Path):
        (vault / "Approved" / "task.md").write_text("yes")
        assert gate.is_approved("task.md") is True

    def test_not_approved(self, gate: GoldSafetyGate):
        assert gate.is_approved("task.md") is False


class TestPendingCount:
    def test_zero_when_empty(self, gate: GoldSafetyGate):
        assert gate.pending_count == 0

    def test_counts_files(self, gate: GoldSafetyGate, vault: Path):
        (vault / "Pending_Approval" / "a.md").write_text("x")
        (vault / "Pending_Approval" / "b.md").write_text("y")
        assert gate.pending_count == 2
