"""
T051 — Integration test: Dashboard real-time updates.

Verifies that:
  1. Dashboard starts empty (or with no missions)
  2. After creating a plan and reconciling, the new plan appears
  3. After completing a step and reconciling, progress updates
  4. Recent Activity log reflects last reasoning log entries
  5. Reconcile runs in under 5 seconds (latency target)
"""

import time
from pathlib import Path

import pytest

from agents.skills.managing_obsidian_vault.dashboard_reconciler import DashboardReconciler
from agents.skills.managing_obsidian_vault.plan_manager import PlanManager


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    (tmp_path / "Plans").mkdir()
    (tmp_path / "Done" / "Plans").mkdir(parents=True)
    (tmp_path / "Pending_Approval").mkdir()
    return tmp_path


@pytest.fixture
def plan_mgr(vault: Path) -> PlanManager:
    return PlanManager(vault_root=vault)


@pytest.fixture
def reconciler(vault: Path) -> DashboardReconciler:
    return DashboardReconciler(vault_root=vault)


# ---------------------------------------------------------------------------
# Test 1: Empty vault → Dashboard shows no missions
# ---------------------------------------------------------------------------

def test_empty_vault_dashboard_shows_idle(reconciler: DashboardReconciler, vault: Path):
    """Empty vault should produce a valid dashboard with 'no missions' message."""
    reconciler.reconcile()
    content = (vault / "Dashboard.md").read_text(encoding="utf-8")

    assert "⚡ Current Missions" in content
    assert "No active missions" in content


# ---------------------------------------------------------------------------
# Test 2: New plan appears after reconcile
# ---------------------------------------------------------------------------

def test_new_plan_appears_after_reconcile(
    plan_mgr: PlanManager, reconciler: DashboardReconciler, vault: Path
):
    """After creating a plan and reconciling, it appears in the dashboard."""
    # Initial reconcile — no missions
    reconciler.reconcile()
    content_before = (vault / "Dashboard.md").read_text(encoding="utf-8")
    assert "No active missions" in content_before

    # Create plan
    plan_mgr.create_plan(
        task_id="RT-001",
        objective="Real-time update test plan",
        context="Testing dashboard latency.",
        steps=["Step 1", "Step 2", "Step 3"],
        priority="medium",
    )
    plan = plan_mgr.load_plan("RT-001")
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-RT-001.md", plan)

    # Reconcile again
    reconciler.reconcile()
    content_after = (vault / "Dashboard.md").read_text(encoding="utf-8")
    assert "Real-time update test plan" in content_after
    assert "No active missions" not in content_after


# ---------------------------------------------------------------------------
# Test 3: Progress updates after step completion
# ---------------------------------------------------------------------------

def test_progress_updates_after_step_complete(
    plan_mgr: PlanManager, reconciler: DashboardReconciler, vault: Path
):
    """Completing a step and reconciling must update the progress bar."""
    plan_mgr.create_plan(
        task_id="RT-002",
        objective="Progress tracking test",
        context="Steps 1-4.",
        steps=["Step 1", "Step 2", "Step 3", "Step 4"],
        priority="low",
    )
    plan = plan_mgr.load_plan("RT-002")
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-RT-002.md", plan)

    reconciler.reconcile()
    content_0 = (vault / "Dashboard.md").read_text(encoding="utf-8")
    assert "0%" in content_0

    # Complete step 1 and 2
    plan_mgr.update_step("RT-002", 1, completed=True, log_entry="Step 1 done")
    plan_mgr.update_step("RT-002", 2, completed=True, log_entry="Step 2 done")

    reconciler.reconcile()
    content_50 = (vault / "Dashboard.md").read_text(encoding="utf-8")
    assert "50%" in content_50


# ---------------------------------------------------------------------------
# Test 4: Recent Activity shows reasoning log entries
# ---------------------------------------------------------------------------

def test_recent_activity_shows_log_entries(
    plan_mgr: PlanManager, reconciler: DashboardReconciler, vault: Path
):
    """Reasoning log entries must appear in the Recent Activity section."""
    plan_mgr.create_plan(
        task_id="RT-003",
        objective="Activity log test",
        context="Checking audit trail.",
        steps=["Write report"],
        priority="medium",
    )
    plan = plan_mgr.load_plan("RT-003")
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-RT-003.md", plan)

    plan_mgr.append_reasoning_log(
        plan_id="RT-003",
        action="Started report preparation",
        rationale="Beginning execution of active plan RT-003",
    )

    reconciler.reconcile()
    content = (vault / "Dashboard.md").read_text(encoding="utf-8")

    assert "🕐 Recent Activity" in content
    assert "Started report preparation" in content


# ---------------------------------------------------------------------------
# Test 5: Reconcile completes in under 5 seconds
# ---------------------------------------------------------------------------

def test_reconcile_latency_under_5_seconds(
    plan_mgr: PlanManager, reconciler: DashboardReconciler, vault: Path
):
    """ReconcileDashboard must complete in under 5 seconds."""
    # Create 5 plans to simulate real-world vault load
    for i in range(1, 6):
        plan_mgr.create_plan(
            task_id=f"PERF-{i:03d}",
            objective=f"Performance test plan {i}",
            context="Load test.",
            steps=[f"Step {j}" for j in range(1, 6)],
            priority="low",
        )
        plan = plan_mgr.load_plan(f"PERF-{i:03d}")
        plan.metadata.status = "Active"
        plan_mgr._write_plan_file(
            vault / "Plans" / f"PLAN-PERF-{i:03d}.md", plan
        )

    start = time.perf_counter()
    reconciler.reconcile()
    elapsed = time.perf_counter() - start

    assert elapsed < 5.0, f"ReconcileDashboard took {elapsed:.2f}s (target < 5s)"
