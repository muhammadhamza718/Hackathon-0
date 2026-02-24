"""
T059 — Integration test: Multiple concurrent blocked plans.

Verifies that when multiple plans are blocked simultaneously:
  1. Dashboard correctly identifies which plans are blocked vs active
  2. Correct approval requests are associated with each plan
  3. Each plan can be unblocked independently without affecting others
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


def _create_plan(plan_mgr, vault, task_id, blocked=True):
    """Helper: create a plan, optionally set status to Active."""
    plan_mgr.create_plan(
        task_id=task_id,
        objective=f"Objective for {task_id}",
        context="Multi-block test context.",
        steps=["Step 1", "✋ Step 2 (approval needed)", "Step 3"],
        priority="high",
    )
    plan = plan_mgr.load_plan(task_id)
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / f"PLAN-{task_id}.md", plan)
    return plan


# ---------------------------------------------------------------------------
# Test 1: Dashboard identifies exactly which plans are blocked vs active
# ---------------------------------------------------------------------------

def test_dashboard_identifies_blocked_vs_active(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    reconciler: DashboardReconciler,
    vault: Path,
):
    """Dashboard must correctly show 2 blocked and 1 active plan."""
    # Create 3 plans
    for tid in ["CONC-001", "CONC-002", "CONC-003"]:
        _create_plan(plan_mgr, vault, tid)

    # Block CONC-001 and CONC-002, leave CONC-003 active
    approval_mgr.draft_external_action(
        action_type="email",
        target_recipient="approver1@example.com",
        plan_id="PLAN-CONC-001",
        step_id=2,
        draft_content="Approval needed for plan 1.",
        rationale="Step 2 of plan 1.",
    )
    approval_mgr.draft_external_action(
        action_type="payment",
        target_recipient="finance@example.com",
        plan_id="PLAN-CONC-002",
        step_id=2,
        draft_content="Payment approval needed for plan 2.",
        rationale="Step 2 of plan 2.",
    )

    block_mgr.detect_blocks()
    reconciler.reconcile()

    content = (vault / "Dashboard.md").read_text(encoding="utf-8")

    # Statistics table checks
    assert "| 🟢 Active Plans | 1 |" in content
    assert "| 🔴 Blocked Plans | 2 |" in content

    # Status badges in missions section
    assert "🔴 Blocked: Awaiting Human Approval" in content
    assert "🟢 Active" in content


# ---------------------------------------------------------------------------
# Test 2: Each blocked plan has its own approval file
# ---------------------------------------------------------------------------

def test_each_blocked_plan_has_own_approval(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    vault: Path,
):
    """Each blocked plan must have a distinct approval file in /Pending_Approval/."""
    for tid in ["IND-001", "IND-002"]:
        _create_plan(plan_mgr, vault, tid)
        approval_mgr.draft_external_action(
            action_type="email",
            target_recipient=f"approver-{tid}@example.com",
            plan_id=f"PLAN-{tid}",
            step_id=2,
            draft_content=f"Approval for {tid}.",
            rationale=f"Step 2 of {tid}.",
        )

    block_mgr.detect_blocks()

    pending_files = list((vault / "Pending_Approval").glob("*.md"))
    assert len(pending_files) == 2

    contents = [f.read_text(encoding="utf-8") for f in pending_files]
    plan_ids_in_files = set()
    for c in contents:
        for line in c.splitlines():
            if line.startswith("plan_id:"):
                plan_ids_in_files.add(line.split(":", 1)[1].strip().strip("'\""))

    assert "PLAN-IND-001" in plan_ids_in_files
    assert "PLAN-IND-002" in plan_ids_in_files


# ---------------------------------------------------------------------------
# Test 3: Unblocking one plan does not unblock the other
# ---------------------------------------------------------------------------

def test_unblock_one_plan_leaves_other_blocked(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    vault: Path,
):
    """Resolving block on SOLO-001 must leave SOLO-002 still Blocked."""
    for i, tid in enumerate(["SOLO-001", "SOLO-002"], start=1):
        _create_plan(plan_mgr, vault, tid)
        approval_mgr.draft_external_action(
            action_type="email",
            target_recipient=f"solo{i}@example.com",
            plan_id=f"PLAN-{tid}",
            step_id=2,
            draft_content=f"Approval for {tid}.",
            rationale=f"Step 2 of {tid}.",
        )

    block_mgr.detect_blocks()

    # Find approval file for SOLO-001
    pending = list((vault / "Pending_Approval").glob("*.md"))
    solo001_file = next(
        f for f in pending if "SOLO-001" in f.read_text(encoding="utf-8")
    )

    # Approve SOLO-001
    shutil.move(
        str(solo001_file),
        str(vault / "Approved" / solo001_file.name),
    )
    block_mgr.resolve_block(solo001_file.name)

    plan_001 = plan_mgr.load_plan("SOLO-001")
    plan_002 = plan_mgr.load_plan("SOLO-002")

    assert plan_001.metadata.status == "Active"
    assert plan_002.metadata.status == "Blocked"


# ---------------------------------------------------------------------------
# Test 4: Dashboard updates correctly after partial unblock
# ---------------------------------------------------------------------------

def test_dashboard_updates_after_partial_unblock(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    reconciler: DashboardReconciler,
    vault: Path,
):
    """After resolving one of two blocked plans, stats must show 1 blocked, 1 active."""
    for i, tid in enumerate(["PART-001", "PART-002"], start=1):
        _create_plan(plan_mgr, vault, tid)
        approval_mgr.draft_external_action(
            action_type="email",
            target_recipient=f"part{i}@example.com",
            plan_id=f"PLAN-{tid}",
            step_id=2,
            draft_content=f"Approval for {tid}.",
            rationale=f"Step 2 of {tid}.",
        )

    block_mgr.detect_blocks()

    # Resolve PART-001 only
    pending = list((vault / "Pending_Approval").glob("*.md"))
    part001_file = next(
        f for f in pending if "PART-001" in f.read_text(encoding="utf-8")
    )
    shutil.move(
        str(part001_file),
        str(vault / "Approved" / part001_file.name),
    )
    block_mgr.resolve_block(part001_file.name)
    reconciler.reconcile()

    content = (vault / "Dashboard.md").read_text(encoding="utf-8")
    assert "| 🟢 Active Plans | 1 |" in content
    assert "| 🔴 Blocked Plans | 1 |" in content


# ---------------------------------------------------------------------------
# Test 5: scan_all_blocks returns all currently blocked plans
# ---------------------------------------------------------------------------

def test_scan_all_blocks_returns_all_blocked(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    vault: Path,
):
    """scan_all_blocks must return BlockInfo for every currently blocked plan."""
    for i, tid in enumerate(["SCAN-001", "SCAN-002", "SCAN-003"], start=1):
        _create_plan(plan_mgr, vault, tid)
        approval_mgr.draft_external_action(
            action_type="email",
            target_recipient=f"approver{i}@example.com",
            plan_id=f"PLAN-{tid}",
            step_id=2,
            draft_content=f"Approval for {tid}.",
            rationale=f"Step 2 of {tid}.",
        )

    block_mgr.detect_blocks()
    all_blocks = block_mgr.scan_all_blocks()

    blocked_ids = {b.plan_id for b in all_blocks}
    assert "SCAN-001" in blocked_ids or "PLAN-SCAN-001" in blocked_ids
    assert "SCAN-002" in blocked_ids or "PLAN-SCAN-002" in blocked_ids
    assert "SCAN-003" in blocked_ids or "PLAN-SCAN-003" in blocked_ids
    assert len(all_blocks) == 3
