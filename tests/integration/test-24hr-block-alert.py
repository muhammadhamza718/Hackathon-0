"""
T058 — Integration test: 24-hour block alert.

Verifies that when a plan has been blocked for > 24 hours, the dashboard
generates a ⚠️ alert in the 🚨 Alerts section.

Uses reconcile_with_time() to inject a 'now' timestamp 25 hours in the future,
simulating time passage without actual sleep().
"""

from datetime import datetime, timedelta, timezone
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
# Test 1: No 24h alert for fresh block
# ---------------------------------------------------------------------------

def test_no_alert_for_fresh_block(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    reconciler: DashboardReconciler,
    vault: Path,
):
    """A block created just now must NOT trigger a 24h alert."""
    plan_mgr.create_plan(
        task_id="STALE-001",
        objective="Fresh block test",
        context="Just created.",
        steps=["Step A", "✋ Step B"],
        priority="medium",
    )
    plan = plan_mgr.load_plan("STALE-001")
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-STALE-001.md", plan)

    approval_mgr.draft_external_action(
        action_type="email",
        target_recipient="hr@example.com",
        plan_id="PLAN-STALE-001",
        step_id=2,
        draft_content="HR notification.",
        rationale="Step B requires approval.",
    )
    block_mgr.detect_blocks()

    # Reconcile with current time (block is fresh)
    reconciler.reconcile_with_time(now_override=None)
    content = (vault / "Dashboard.md").read_text(encoding="utf-8")
    assert "No active alerts." in content


# ---------------------------------------------------------------------------
# Test 2: 24h alert triggers when block is 25 hours old
# ---------------------------------------------------------------------------

def test_24h_alert_triggers_after_threshold(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    reconciler: DashboardReconciler,
    vault: Path,
):
    """A block older than 24h must appear in 🚨 Alerts section."""
    plan_mgr.create_plan(
        task_id="STALE-002",
        objective="Stale block alert test",
        context="Blocked yesterday.",
        steps=["Step A", "✋ Step B"],
        priority="high",
    )
    plan = plan_mgr.load_plan("STALE-002")
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-STALE-002.md", plan)

    approval_mgr.draft_external_action(
        action_type="payment",
        target_recipient="vendor@example.com",
        plan_id="PLAN-STALE-002",
        step_id=2,
        draft_content="Payment approval needed.",
        rationale="Step B requires payment approval.",
    )
    block_mgr.detect_blocks()

    # Simulate 25 hours in the future
    simulated_now = datetime.now(timezone.utc) + timedelta(hours=25)
    reconciler.reconcile_with_time(now_override=simulated_now)
    content = (vault / "Dashboard.md").read_text(encoding="utf-8")

    assert "🚨 Alerts" in content
    assert "⚠️" in content
    assert "STALE-002" in content
    assert "No active alerts." not in content


# ---------------------------------------------------------------------------
# Test 3: Alert includes plan ID, duration, and approval context
# ---------------------------------------------------------------------------

def test_alert_includes_required_fields(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    reconciler: DashboardReconciler,
    vault: Path,
):
    """Alert message must include plan ID, hours blocked, and approval context."""
    plan_mgr.create_plan(
        task_id="STALE-003",
        objective="Alert content validation",
        context="Alert field check.",
        steps=["Step A", "✋ Send invoice"],
        priority="high",
    )
    plan = plan_mgr.load_plan("STALE-003")
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-STALE-003.md", plan)

    approval_mgr.draft_external_action(
        action_type="email",
        target_recipient="client@example.com",
        plan_id="PLAN-STALE-003",
        step_id=2,
        draft_content="Invoice email.",
        rationale="Invoice delivery approval.",
    )
    block_mgr.detect_blocks()

    simulated_now = datetime.now(timezone.utc) + timedelta(hours=26)
    reconciler.reconcile_with_time(now_override=simulated_now)
    content = (vault / "Dashboard.md").read_text(encoding="utf-8")

    # Alert section content (between 🚨 Alerts and next ##)
    alerts_section = content.split("🚨 Alerts")[1].split("##")[0]
    assert "STALE-003" in alerts_section
    assert "h" in alerts_section          # hours in the message
    assert "/Approved/" in alerts_section  # human action instruction


# ---------------------------------------------------------------------------
# Test 4: Multiple blocked plans each get their own alert if stale
# ---------------------------------------------------------------------------

def test_multiple_stale_plans_each_get_alert(
    plan_mgr: PlanManager,
    approval_mgr: ApprovalManager,
    block_mgr: BlockManager,
    reconciler: DashboardReconciler,
    vault: Path,
):
    """Each stale blocked plan must generate its own alert entry."""
    for i in range(1, 3):
        plan_mgr.create_plan(
            task_id=f"MULTI-{i:03d}",
            objective=f"Multi-stale test {i}",
            context="Multiple stale blocks.",
            steps=["Step A", "✋ Step B"],
            priority="high",
        )
        plan = plan_mgr.load_plan(f"MULTI-{i:03d}")
        plan.metadata.status = "Active"
        plan_mgr._write_plan_file(vault / "Plans" / f"PLAN-MULTI-{i:03d}.md", plan)
        approval_mgr.draft_external_action(
            action_type="email",
            target_recipient=f"user{i}@example.com",
            plan_id=f"PLAN-MULTI-{i:03d}",
            step_id=2,
            draft_content=f"Approval {i}",
            rationale=f"Step B of plan {i}",
        )

    block_mgr.detect_blocks()
    simulated_now = datetime.now(timezone.utc) + timedelta(hours=30)
    reconciler.reconcile_with_time(now_override=simulated_now)
    content = (vault / "Dashboard.md").read_text(encoding="utf-8")

    alerts_section = content.split("🚨 Alerts")[1].split("##")[0]
    assert "MULTI-001" in alerts_section
    assert "MULTI-002" in alerts_section
