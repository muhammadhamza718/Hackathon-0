"""
T056 — Integration test: Block detection when approval pending.

Verifies that after drafting an external action for a HITL step:
  1. BlockManager.detect_blocks() identifies the plan as Blocked
  2. blocked_reason field is populated with approval filename and timestamp
  3. Dashboard shows "Blocked: Awaiting Human Approval"
"""

from pathlib import Path

import pytest

from agents.skills.managing_obsidian_vault.approval_manager import ApprovalManager
from agents.skills.managing_obsidian_vault.block_manager import BlockManager
from agents.skills.managing_obsidian_vault.dashboard_reconciler import DashboardReconciler
from agents.skills.managing_obsidian_vault.plan_manager import PlanManager


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    (tmp_path / "Plans").mkdir()
    (tmp_path / "Done" / "Plans").mkdir(parents=True)
    (tmp_path / "Pending_Approval").mkdir()
    (tmp_path / "Approved").mkdir()
    (tmp_path / "Rejected").mkdir()
    (tmp_path / "Done" / "Actions").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def plan_mgr(vault: Path) -> PlanManager:
    return PlanManager(vault_root=vault)


@pytest.fixture
def approval_mgr(vault: Path) -> ApprovalManager:
    return ApprovalManager(vault_root=vault)


@pytest.fixture
def block_mgr(vault: Path) -> BlockManager:
    return BlockManager(vault_root=vault)


@pytest.fixture
def reconciler(vault: Path) -> DashboardReconciler:
    return DashboardReconciler(vault_root=vault)


# ---------------------------------------------------------------------------
# Test 1: detect_blocks identifies plan as Blocked when approval pending
# ---------------------------------------------------------------------------

def test_detect_blocks_marks_plan_blocked(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    vault: Path,
):
    """Plan must be identified as Blocked when it has a pending approval file."""
    plan_mgr.create_plan(
        task_id="BLK-001",
        objective="Send invoice to Client A",
        context="Invoice required.",
        steps=["Prepare invoice", "✋ Send email"],
        priority="high",
    )
    plan = plan_mgr.load_plan("BLK-001")
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-BLK-001.md", plan)

    # Draft approval for HITL step
    approval_mgr.draft_external_action(
        action_type="email",
        target_recipient="client@example.com",
        plan_id="PLAN-BLK-001",
        step_id=2,
        draft_content="Dear Client, invoice attached.",
        rationale="Step 2 requires email approval.",
    )

    blocks = block_mgr.detect_blocks()

    assert len(blocks) == 1
    assert blocks[0].plan_id == "BLK-001"


# ---------------------------------------------------------------------------
# Test 2: Plan status updated to Blocked in file
# ---------------------------------------------------------------------------

def test_detect_blocks_updates_plan_status_in_file(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    vault: Path,
):
    """After detect_blocks, plan file status must be 'Blocked'."""
    plan_mgr.create_plan(
        task_id="BLK-002",
        objective="Post to social media",
        context="Marketing campaign.",
        steps=["Draft post", "✋ Publish post"],
        priority="medium",
    )
    plan = plan_mgr.load_plan("BLK-002")
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-BLK-002.md", plan)

    approval_mgr.draft_external_action(
        action_type="social_post",
        target_recipient="twitter",
        plan_id="PLAN-BLK-002",
        step_id=2,
        draft_content="Exciting news from our team!",
        rationale="Social post requires approval.",
    )

    block_mgr.detect_blocks()

    # Re-load plan and check status
    updated = plan_mgr.load_plan("BLK-002")
    assert updated.metadata.status == "Blocked"


# ---------------------------------------------------------------------------
# Test 3: blocked_reason field populated
# ---------------------------------------------------------------------------

def test_blocked_reason_populated(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    vault: Path,
):
    """blocked_reason must reference the approval filename and waiting time."""
    plan_mgr.create_plan(
        task_id="BLK-003",
        objective="Execute payment to vendor",
        context="Finance flow.",
        steps=["Calculate amount", "✋ Execute payment"],
        priority="high",
    )
    plan = plan_mgr.load_plan("BLK-003")
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-BLK-003.md", plan)

    approval_mgr.draft_external_action(
        action_type="payment",
        target_recipient="vendor@example.com",
        plan_id="PLAN-BLK-003",
        step_id=2,
        draft_content="Payment of $5,000 to Vendor X",
        rationale="Step 2 requires payment approval.",
    )

    block_mgr.detect_blocks()
    updated = plan_mgr.load_plan("BLK-003")

    assert updated.metadata.blocked_reason is not None
    # blocked_reason contains the approval filename (which includes timestamp+action_type+recipient)
    # and the step info — verify it has the key markers
    assert "Approval request" in updated.metadata.blocked_reason
    assert "Step 2" in updated.metadata.blocked_reason


# ---------------------------------------------------------------------------
# Test 4: Dashboard shows Blocked status after detect_blocks
# ---------------------------------------------------------------------------

def test_dashboard_shows_blocked_after_detect_blocks(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    reconciler: DashboardReconciler,
    vault: Path,
):
    """Dashboard must reflect Blocked status after block detection."""
    plan_mgr.create_plan(
        task_id="BLK-004",
        objective="Send client report",
        context="Quarterly report.",
        steps=["Generate report", "✋ Email report to client"],
        priority="medium",
    )
    plan = plan_mgr.load_plan("BLK-004")
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-BLK-004.md", plan)

    approval_mgr.draft_external_action(
        action_type="email",
        target_recipient="client@example.com",
        plan_id="PLAN-BLK-004",
        step_id=2,
        draft_content="Q4 report attached.",
        rationale="Email requires approval.",
    )

    block_mgr.detect_blocks()
    reconciler.reconcile()

    content = (vault / "Dashboard.md").read_text(encoding="utf-8")
    assert "🔴 Blocked: Awaiting Human Approval" in content


# ---------------------------------------------------------------------------
# Test 5: No blocks when no pending approvals
# ---------------------------------------------------------------------------

def test_no_blocks_when_no_pending_approvals(
    plan_mgr: PlanManager,
    block_mgr: BlockManager,
    vault: Path,
):
    """detect_blocks must return empty list when no files are in /Pending_Approval/."""
    plan_mgr.create_plan(
        task_id="CLEAN-001",
        objective="Clean plan with no external actions",
        context="Pure internal task.",
        steps=["Step A", "Step B"],
        priority="low",
    )

    blocks = block_mgr.detect_blocks()
    assert blocks == []
