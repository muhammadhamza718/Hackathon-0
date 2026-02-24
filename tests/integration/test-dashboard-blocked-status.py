"""
T050 — Integration test: Dashboard shows blocked status.

Verifies that when a plan has a ✋ (HITL) step and an approval request is
pending, ReconcileDashboard reflects the Blocked state with the correct badge
and pending approval count.
"""

from pathlib import Path

import pytest

from agents.skills.managing_obsidian_vault.approval_manager import ApprovalManager
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
def reconciler(vault: Path) -> DashboardReconciler:
    return DashboardReconciler(vault_root=vault)


# ---------------------------------------------------------------------------
# Test 1: Blocked plan shows 🔴 badge
# ---------------------------------------------------------------------------

def test_blocked_plan_shows_red_badge(
    plan_mgr: PlanManager, reconciler: DashboardReconciler, vault: Path
):
    """Plan with status=Blocked must show 🔴 Blocked badge."""
    plan_mgr.create_plan(
        task_id="2026-003",
        objective="Send invoice to Client B",
        context="Awaiting approval.",
        steps=["Prepare invoice", "✋ Send email with invoice"],
        priority="high",
    )
    plan = plan_mgr.load_plan("2026-003")
    plan.metadata.status = "Blocked"
    plan.metadata.blocked_reason = "Awaiting email approval"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-2026-003.md", plan)

    reconciler.reconcile()
    content = (vault / "Dashboard.md").read_text(encoding="utf-8")

    assert "🔴 Blocked: Awaiting Human Approval" in content


# ---------------------------------------------------------------------------
# Test 2: Pending approval count appears when files in /Pending_Approval/
# ---------------------------------------------------------------------------

def test_pending_approval_count_shown(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    reconciler: DashboardReconciler,
    vault: Path,
):
    """If plan has pending approvals, dashboard must show the count."""
    plan_mgr.create_plan(
        task_id="2026-003",
        objective="Send invoice to Client B",
        context="Awaiting approval.",
        steps=["Prepare invoice", "✋ Send email with invoice"],
        priority="high",
    )
    plan = plan_mgr.load_plan("2026-003")
    plan.metadata.status = "Blocked"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-2026-003.md", plan)

    # Draft an approval request for this plan
    approval_mgr.draft_external_action(
        action_type="email",
        target_recipient="clientb@example.com",
        plan_id="PLAN-2026-003",
        step_id=2,
        draft_content="Dear Client B, invoice attached.",
        rationale="Step 2 requires email approval.",
    )

    reconciler.reconcile()
    content = (vault / "Dashboard.md").read_text(encoding="utf-8")
    assert "Pending Approvals" in content
    assert "/Pending_Approval/" in content


# ---------------------------------------------------------------------------
# Test 3: Blocked section distinguishes from Active
# ---------------------------------------------------------------------------

def test_blocked_and_active_shown_separately(
    plan_mgr: PlanManager, reconciler: DashboardReconciler, vault: Path
):
    """Dashboard must show both Active and Blocked plans correctly."""
    # Active plan
    plan_mgr.create_plan(
        task_id="ACT-001",
        objective="Run quarterly audit",
        context="Finance.",
        steps=["Collect data"],
        priority="medium",
    )
    plan_a = plan_mgr.load_plan("ACT-001")
    plan_a.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-ACT-001.md", plan_a)

    # Blocked plan
    plan_mgr.create_plan(
        task_id="BLK-001",
        objective="Send payment to Vendor X",
        context="Awaiting payment approval.",
        steps=["Calculate amount", "✋ Execute payment"],
        priority="high",
    )
    plan_b = plan_mgr.load_plan("BLK-001")
    plan_b.metadata.status = "Blocked"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-BLK-001.md", plan_b)

    reconciler.reconcile()
    content = (vault / "Dashboard.md").read_text(encoding="utf-8")

    assert "🟢 Active" in content
    assert "🔴 Blocked: Awaiting Human Approval" in content
    assert "| 🟢 Active Plans | 1 |" in content
    assert "| 🔴 Blocked Plans | 1 |" in content


# ---------------------------------------------------------------------------
# Test 4: No alerts for recently blocked plan (< 24 h)
# ---------------------------------------------------------------------------

def test_no_alert_for_recently_blocked_plan(
    plan_mgr: PlanManager, reconciler: DashboardReconciler, vault: Path
):
    """Plans blocked less than 24 hours ago must NOT appear in Alerts."""
    plan_mgr.create_plan(
        task_id="NEW-BLK",
        objective="New blocked plan",
        context="Just created.",
        steps=["Step A", "✋ Step B"],
        priority="low",
    )
    plan = plan_mgr.load_plan("NEW-BLK")
    plan.metadata.status = "Blocked"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-NEW-BLK.md", plan)

    reconciler.reconcile()
    content = (vault / "Dashboard.md").read_text(encoding="utf-8")

    # Should show Alerts section but no stale-block entries
    assert "🚨 Alerts" in content
    # The plan is recent; stale alert should NOT be triggered
    assert "No active alerts." in content or "PLAN-NEW-BLK" not in content.split("🚨")[1].split("##")[0]
