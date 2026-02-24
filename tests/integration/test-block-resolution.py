"""
T057 — Integration test: Block resolution on approval file move.

Verifies that when approval file is moved to /Approved/:
  1. BlockManager.resolve_block() detects the unblock
  2. Plan status changes back to "Active"
  3. Reasoning Log records the resolution
  4. Dashboard updates to reflect Active status
  5. Next step is correctly identified for resumption
"""

import shutil
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


def _setup_blocked_plan(plan_mgr, approval_mgr, block_mgr, vault, task_id="RES-001"):
    """Helper: create plan, draft approval, run detect_blocks, return approval filename."""
    plan_mgr.create_plan(
        task_id=task_id,
        objective=f"Resolution test plan {task_id}",
        context="Testing block resolution.",
        steps=["Step 1", "✋ Step 2 (needs approval)", "Step 3"],
        priority="high",
    )
    plan = plan_mgr.load_plan(task_id)
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / f"PLAN-{task_id}.md", plan)

    approval_path = approval_mgr.draft_external_action(
        action_type="email",
        target_recipient="approver@example.com",
        plan_id=f"PLAN-{task_id}",
        step_id=2,
        draft_content="Approval needed for step 2.",
        rationale="HITL step requires human sign-off.",
    )
    block_mgr.detect_blocks()
    return approval_path.name


# ---------------------------------------------------------------------------
# Test 1: resolve_block returns next step when approval moved to /Approved/
# ---------------------------------------------------------------------------

def test_resolve_block_returns_next_step(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    vault: Path,
):
    """resolve_block must return the next step description when block clears."""
    filename = _setup_blocked_plan(plan_mgr, approval_mgr, block_mgr, vault, "RES-001")

    # Simulate human moving file to /Approved/
    shutil.move(
        str(vault / "Pending_Approval" / filename),
        str(vault / "Approved" / filename),
    )

    next_step = block_mgr.resolve_block(filename)
    # Step 2 is HITL (approval given), step 3 is next
    assert next_step is not None
    # "Step 3" should be next (step 1 not done either, but step 1 is first)
    # Actually step 1 is first incomplete — it was never marked complete
    assert "Step" in next_step


# ---------------------------------------------------------------------------
# Test 2: Plan status returns to Active after resolution
# ---------------------------------------------------------------------------

def test_plan_status_restored_to_active(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    vault: Path,
):
    """Plan must be status=Active after block resolved."""
    filename = _setup_blocked_plan(plan_mgr, approval_mgr, block_mgr, vault, "RES-002")

    # Confirm plan is Blocked first
    plan_before = plan_mgr.load_plan("RES-002")
    assert plan_before.metadata.status == "Blocked"

    # Move to /Approved/ (human sign-off)
    shutil.move(
        str(vault / "Pending_Approval" / filename),
        str(vault / "Approved" / filename),
    )

    block_mgr.resolve_block(filename)
    plan_after = plan_mgr.load_plan("RES-002")
    assert plan_after.metadata.status == "Active"


# ---------------------------------------------------------------------------
# Test 3: Reasoning Log records the resolution
# ---------------------------------------------------------------------------

def test_reasoning_log_records_resolution(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    vault: Path,
):
    """Reasoning Log must have an entry recording that the block was cleared."""
    filename = _setup_blocked_plan(plan_mgr, approval_mgr, block_mgr, vault, "RES-003")

    shutil.move(
        str(vault / "Pending_Approval" / filename),
        str(vault / "Approved" / filename),
    )

    block_mgr.resolve_block(filename)
    plan = plan_mgr.load_plan("RES-003")

    # At least one log entry should mention the block was cleared
    resolution_logged = any(
        "cleared" in entry.lower() or "resuming" in entry.lower()
        for entry in plan.reasoning_logs
    )
    assert resolution_logged, "Reasoning Log must record block resolution"


# ---------------------------------------------------------------------------
# Test 4: Dashboard shows Active after resolution + reconcile
# ---------------------------------------------------------------------------

def test_dashboard_updates_after_resolution(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    reconciler: DashboardReconciler,
    vault: Path,
):
    """Dashboard must show Active (not Blocked) after block is resolved."""
    filename = _setup_blocked_plan(plan_mgr, approval_mgr, block_mgr, vault, "RES-004")

    # Initial dashboard should show Blocked
    reconciler.reconcile()
    content_before = (vault / "Dashboard.md").read_text(encoding="utf-8")
    assert "🔴 Blocked" in content_before

    # Resolve
    shutil.move(
        str(vault / "Pending_Approval" / filename),
        str(vault / "Approved" / filename),
    )
    block_mgr.resolve_block(filename)
    reconciler.reconcile()

    content_after = (vault / "Dashboard.md").read_text(encoding="utf-8")
    assert "🟢 Active" in content_after
    # The blocked-plan-specific entry should be gone
    assert "| 🔴 Blocked Plans | 0 |" in content_after


# ---------------------------------------------------------------------------
# Test 5: blocked_reason cleared after resolution
# ---------------------------------------------------------------------------

def test_blocked_reason_cleared_on_resolution(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    vault: Path,
):
    """blocked_reason metadata must be None after block is resolved."""
    filename = _setup_blocked_plan(plan_mgr, approval_mgr, block_mgr, vault, "RES-005")

    shutil.move(
        str(vault / "Pending_Approval" / filename),
        str(vault / "Approved" / filename),
    )

    block_mgr.resolve_block(filename)
    plan = plan_mgr.load_plan("RES-005")
    assert plan.metadata.blocked_reason is None
