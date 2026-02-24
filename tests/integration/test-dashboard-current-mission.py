"""
T049 — Integration test: Dashboard reflects current mission.

Verifies that after creating an active plan, ReconcileDashboard:
  1. Creates/updates Dashboard.md
  2. Shows plan objective in ⚡ Current Missions section
  3. Shows correct status badge (🟢 Active)
  4. Shows accurate step progress
"""

from pathlib import Path

import pytest

from agents.skills.managing_obsidian_vault.dashboard_reconciler import DashboardReconciler
from agents.skills.managing_obsidian_vault.plan_manager import PlanManager


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """Minimal vault structure."""
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
# Test 1: Dashboard created after plan exists
# ---------------------------------------------------------------------------

def test_dashboard_created_on_reconcile(
    plan_mgr: PlanManager, reconciler: DashboardReconciler, vault: Path
):
    """Dashboard.md should be created after reconcile."""
    plan_mgr.create_plan(
        task_id="2026-001",
        objective="Generate and send invoice to Client A",
        context="Client requested via email.",
        steps=["Prepare invoice", "Calculate amount", "✋ Send email"],
        priority="high",
    )
    # Change status to Active
    plan = plan_mgr.load_plan("2026-001")
    plan.metadata.status = "Active"
    plan_path = vault / "Plans" / "PLAN-2026-001.md"
    plan_mgr._write_plan_file(plan_path, plan)

    dash_path = reconciler.reconcile()
    assert dash_path.exists()


# ---------------------------------------------------------------------------
# Test 2: Plan objective appears in Current Missions
# ---------------------------------------------------------------------------

def test_current_missions_shows_objective(
    plan_mgr: PlanManager, reconciler: DashboardReconciler, vault: Path
):
    """Plan objective must appear in the ⚡ Current Missions section."""
    plan_mgr.create_plan(
        task_id="2026-001",
        objective="Generate and send invoice to Client A",
        context="Client request.",
        steps=["Prepare invoice", "Calculate amount"],
        priority="high",
    )
    plan = plan_mgr.load_plan("2026-001")
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-2026-001.md", plan)

    reconciler.reconcile()
    content = (vault / "Dashboard.md").read_text(encoding="utf-8")

    assert "Generate and send invoice to Client A" in content
    assert "⚡ Current Missions" in content


# ---------------------------------------------------------------------------
# Test 3: Status badge is 🟢 Active for active plans
# ---------------------------------------------------------------------------

def test_active_plan_shows_green_badge(
    plan_mgr: PlanManager, reconciler: DashboardReconciler, vault: Path
):
    """Active plan must show 🟢 Active status badge."""
    plan_mgr.create_plan(
        task_id="2026-001",
        objective="Run monthly report",
        context="Monthly cycle.",
        steps=["Collect data", "Compile report"],
        priority="medium",
    )
    plan = plan_mgr.load_plan("2026-001")
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-2026-001.md", plan)

    reconciler.reconcile()
    content = (vault / "Dashboard.md").read_text(encoding="utf-8")
    assert "🟢 Active" in content


# ---------------------------------------------------------------------------
# Test 4: Step progress matches plan state
# ---------------------------------------------------------------------------

def test_step_progress_accurate(
    plan_mgr: PlanManager, reconciler: DashboardReconciler, vault: Path
):
    """Progress bar must reflect actual step completion count."""
    plan_mgr.create_plan(
        task_id="2026-002",
        objective="Audit Q1 expenses",
        context="Finance team request.",
        steps=["Collect receipts", "Categorise expenses", "Generate report"],
        priority="medium",
    )
    # Mark step 1 complete
    plan_mgr.update_step("2026-002", 1, completed=True, log_entry="Collected all receipts")

    plan = plan_mgr.load_plan("2026-002")
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-2026-002.md", plan)

    reconciler.reconcile()
    content = (vault / "Dashboard.md").read_text(encoding="utf-8")
    # 1/3 steps done = 33%
    assert "33%" in content


# ---------------------------------------------------------------------------
# Test 5: Plan Statistics shows correct counts
# ---------------------------------------------------------------------------

def test_plan_statistics_counts(
    plan_mgr: PlanManager, reconciler: DashboardReconciler, vault: Path
):
    """Plan Statistics section must have correct Active, Draft, Done counts."""
    # Create one Active plan
    plan_mgr.create_plan(
        task_id="ACT-001",
        objective="Active plan",
        context="ctx",
        steps=["Step A"],
        priority="high",
    )
    plan = plan_mgr.load_plan("ACT-001")
    plan.metadata.status = "Active"
    plan_mgr._write_plan_file(vault / "Plans" / "PLAN-ACT-001.md", plan)

    # Create one Draft plan
    plan_mgr.create_plan(
        task_id="DRF-001",
        objective="Draft plan",
        context="ctx",
        steps=["Step B"],
        priority="low",
    )

    reconciler.reconcile()
    content = (vault / "Dashboard.md").read_text(encoding="utf-8")

    assert "📊 Plan Statistics" in content
    # 1 Active, 1 Draft
    assert "| 🟢 Active Plans | 1 |" in content
    assert "| ⚪ Draft Plans | 1 |" in content
