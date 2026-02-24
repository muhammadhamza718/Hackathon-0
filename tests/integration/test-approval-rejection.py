"""
T042 — Integration test: Rejection handling.

Verifies that when a human moves the approval file to /Rejected/:
  1. Agent detects rejection via detect_approval_status()
  2. MCP is NOT called
  3. record_rejection() updates the file status
  4. Plan step remains incomplete
"""

from pathlib import Path

import pytest

from agents.skills.managing_obsidian_vault.approval_manager import (
    ApprovalManager,
    ApprovalRequest,
    ApprovalStatus,
)
from agents.skills.managing_obsidian_vault.plan_manager import PlanManager


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    (tmp_path / "Pending_Approval").mkdir()
    (tmp_path / "Approved").mkdir()
    (tmp_path / "Rejected").mkdir()
    (tmp_path / "Done" / "Actions").mkdir(parents=True)
    (tmp_path / "Plans").mkdir()
    return tmp_path


@pytest.fixture
def manager(vault: Path) -> ApprovalManager:
    return ApprovalManager(vault_root=vault)


@pytest.fixture
def plan_mgr(vault: Path) -> PlanManager:
    return PlanManager(vault_root=vault)


def _place_rejected_file(vault: Path, filename: str) -> Path:
    """Write a valid approval file into /Rejected/ (simulating human move)."""
    content = (
        "---\n"
        "action_type: email\n"
        "target_recipient: client@example.com\n"
        "plan_id: PLAN-2026-001\n"
        "step_id: 4\n"
        "rationale: Send invoice to Client A\n"
        "created_date: '2026-02-24T10:00:00Z'\n"
        "status: pending\n"
        "---\n\n"
        "# Email Approval Request\n\n"
        "Dear Client A, invoice attached.\n"
    )
    path = vault / "Rejected" / filename
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Test 1: detect_approval_status returns REJECTED when file in /Rejected/
# ---------------------------------------------------------------------------

def test_detect_rejection_status(manager: ApprovalManager, vault: Path):
    """detect_approval_status must return REJECTED for files in /Rejected/."""
    filename = "2026-02-24T10-00-00Z_email_client.md"
    _place_rejected_file(vault, filename)

    status = manager.detect_approval_status(filename)
    assert status == ApprovalStatus.REJECTED


# ---------------------------------------------------------------------------
# Test 2: MCP is NOT called when status is REJECTED
# ---------------------------------------------------------------------------

def test_mcp_not_called_on_rejection(manager: ApprovalManager, vault: Path):
    """execute_approved_action must raise FileNotFoundError if file is in /Rejected/."""
    filename = "2026-02-24T10-00-00Z_email_client.md"
    _place_rejected_file(vault, filename)

    # File is in /Rejected/, not /Approved/ — execute must refuse
    with pytest.raises(FileNotFoundError):
        manager.execute_approved_action(filename)


# ---------------------------------------------------------------------------
# Test 3: record_rejection updates file status to REJECTED
# ---------------------------------------------------------------------------

def test_record_rejection_updates_status(manager: ApprovalManager, vault: Path):
    """record_rejection must persist status=rejected in the file."""
    filename = "2026-02-24T10-00-00Z_email_client.md"
    _place_rejected_file(vault, filename)

    req = manager.record_rejection(filename)
    assert req.status == ApprovalStatus.REJECTED

    # Verify persisted to disk
    persisted = ApprovalRequest.from_file(vault / "Rejected" / filename)
    assert persisted.status == ApprovalStatus.REJECTED


# ---------------------------------------------------------------------------
# Test 4: Plan step NOT marked complete after rejection
# ---------------------------------------------------------------------------

def test_plan_step_not_completed_after_rejection(
    manager: ApprovalManager,
    plan_mgr: PlanManager,
    vault: Path,
):
    """Plan step 4 must remain incomplete after rejection."""
    # Create a plan with a HITL step
    plan_mgr.create_plan(
        task_id="2026-001",
        objective="Send invoice to Client A",
        context="Step 4 requires email approval",
        steps=[
            "Prepare invoice",
            "Calculate amount",
            "Generate PDF",
            "✋ Send email with invoice attachment",
        ],
        priority="high",
    )

    # Record the rejection (simulate human moved file to /Rejected/)
    filename = "2026-02-24T10-00-00Z_email_client.md"
    _place_rejected_file(vault, filename)
    manager.record_rejection(filename)

    # Plan step 4 must still be incomplete
    plan = plan_mgr.load_plan("2026-001")
    step_4 = plan.steps[3]  # 0-indexed
    assert not step_4.completed, "Step 4 must NOT be marked complete after rejection"
    assert step_4.hitl_required, "Step 4 must retain HITL marker"


# ---------------------------------------------------------------------------
# Test 5: validate_hitl_step_has_approval raises when only rejected file exists
# ---------------------------------------------------------------------------

def test_hitl_validation_fails_when_only_rejected(manager: ApprovalManager, vault: Path):
    """HITL validation must fail if only a rejected file exists (not executed)."""
    filename = "2026-02-24T10-00-00Z_email_client.md"
    _place_rejected_file(vault, filename)

    with pytest.raises(PermissionError, match="no executed approval file found"):
        manager.validate_hitl_step_has_approval(
            plan_id="PLAN-2026-001",
            step_id=4,
        )
