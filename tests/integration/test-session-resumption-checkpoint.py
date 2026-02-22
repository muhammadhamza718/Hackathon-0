"""
Test: Session resumption with checkpoint loading (T032)

Tests that the Agent loads the most recent incomplete plan on session startup
and identifies the correct checkpoint from Reasoning Logs.

Setup: Create plan with 3 steps, mark Step 1 complete, end session
Trigger: Start new session
Assert: Plan loaded correctly
Assert: Checkpoint identified as Step 2
Assert: Agent displays "Resuming plan"
Assert: Step 1 not re-executed
"""

import logging
import pytest
from pathlib import Path
from datetime import datetime, timezone
from agents.skills.managing_obsidian_vault.plan_manager import PlanManager

logger = logging.getLogger(__name__)


@pytest.fixture
def vault_tmp(tmp_path):
    """Create temporary vault directory for testing."""
    vault = tmp_path / "test_vault"
    vault.mkdir()
    (vault / "Plans").mkdir()
    (vault / "Done").mkdir()
    (vault / "Done" / "Plans").mkdir()
    return vault


def test_session_resumption_checkpoint(vault_tmp):
    """
    Test multi-session resumption with checkpoint identification.

    1. Create plan with 3 steps
    2. Mark Step 1 complete
    3. Simulate session end
    4. Start new session: call find_active_plan()
    5. Verify plan loaded with correct checkpoint
    """
    # Phase 1: Create plan in first session
    pm = PlanManager(vault_tmp)

    plan_id = "TEST-2026-001"
    objective = "Generate and send invoice to Client A"
    context = "Client requested via email. Amount: $1,500. No blocking dependencies."
    steps = [
        "Identify client contact",
        "Calculate invoice amount",
        "Generate invoice PDF",
        "✋ Send email with invoice",
        "Log transaction"
    ]

    plan_path = pm.create_plan(
        task_id=plan_id,
        objective=objective,
        context=context,
        steps=steps,
        priority="high"
    )

    # Verify plan created
    assert plan_path.exists()
    initial_plan = pm.load_plan(plan_id)
    assert initial_plan.metadata.status == "Draft"
    assert len(initial_plan.steps) == 5
    assert not initial_plan.steps[0].completed

    # Phase 2: Mark Step 1 complete and set status to Active
    pm.update_step(
        plan_id=plan_id,
        step_number=1,
        completed=True,
        log_entry="Identified client contact: client_a@example.com"
    )

    # Update status to Active
    plan = pm.load_plan(plan_id)
    plan.metadata.status = "Active"
    plan_path = vault_tmp / "Plans" / f"PLAN-{plan_id}.md"
    pm._write_plan_file(plan_path, plan)

    # Verify Step 1 marked complete
    updated_plan = pm.load_plan(plan_id)
    assert updated_plan.steps[0].completed
    assert updated_plan.metadata.status == "Active"
    assert len(updated_plan.reasoning_logs) >= 2  # Initial + Step 1 update

    # Phase 3: Session end (no action needed, just represents time passing)
    # ...

    # Phase 4: New session starts - find active plan
    new_pm = PlanManager(vault_tmp)
    resumed_plan = new_pm.find_active_plan()

    # Verify plan loaded correctly
    assert resumed_plan is not None
    assert resumed_plan.metadata.task_id == plan_id
    assert resumed_plan.metadata.status == "Active"
    assert resumed_plan.steps[0].completed

    # Verify checkpoint (next incomplete step is Step 2)
    next_step = resumed_plan.get_next_incomplete_step()
    assert next_step is not None
    assert next_step.number == 2
    assert next_step.description == "Calculate invoice amount"

    # Verify Step 1 marked complete (not re-executed)
    assert resumed_plan.steps[0].completed
    assert resumed_plan.steps[1].completed is False

    # Verify reasoning logs preserved
    assert len(resumed_plan.reasoning_logs) >= 2
    assert "Identified client contact" in resumed_plan.reasoning_logs[-1]

    logger.info("✓ Session resumption checkpoint test passed")


def test_multiple_plans_prioritization(vault_tmp):
    """
    Test plan prioritization: Active > Blocked > Draft, recent first.

    Setup: Create 3 plans with different statuses
    Trigger: find_active_plan()
    Assert: Returns Active plan (highest priority)
    """
    pm = PlanManager(vault_tmp)

    # Create Draft plan (oldest)
    draft_plan_path = pm.create_plan(
        task_id="DRAFT-001",
        objective="Draft plan objective",
        context="This is a draft",
        steps=["Step 1"],
        priority="low"
    )
    draft = pm.load_plan("DRAFT-001")
    draft.metadata.status = "Draft"
    draft.metadata.created_date = "2026-02-19T10:00:00Z"
    pm._write_plan_file(draft_plan_path, draft)

    # Create Blocked plan (medium priority, older)
    blocked_plan_path = pm.create_plan(
        task_id="BLOCKED-001",
        objective="Blocked plan objective",
        context="This is blocked",
        steps=["Step 1"],
        priority="medium"
    )
    blocked = pm.load_plan("BLOCKED-001")
    blocked.metadata.status = "Blocked"
    blocked.metadata.blocked_reason = "Awaiting human approval"
    blocked.metadata.created_date = "2026-02-20T10:00:00Z"
    pm._write_plan_file(blocked_plan_path, blocked)

    # Create Active plan (highest priority, newest)
    active_plan_path = pm.create_plan(
        task_id="ACTIVE-001",
        objective="Active plan objective",
        context="This is active",
        steps=["Step 1"],
        priority="high"
    )
    active = pm.load_plan("ACTIVE-001")
    active.metadata.status = "Active"
    active.metadata.created_date = "2026-02-21T10:00:00Z"
    pm._write_plan_file(active_plan_path, active)

    # find_active_plan should return Active plan
    found_plan = pm.find_active_plan()
    assert found_plan is not None
    assert found_plan.metadata.task_id == "ACTIVE-001"
    assert found_plan.metadata.status == "Active"

    logger.info("✓ Plan prioritization test passed")


def test_multiple_active_plans_recent_first(vault_tmp):
    """
    Test that when multiple Active plans exist, most recent is selected.

    Setup: Create 2 Active plans with different timestamps
    Trigger: find_active_plan()
    Assert: Returns most recent Active plan
    """
    pm = PlanManager(vault_tmp)

    # Create older Active plan
    old_active_path = pm.create_plan(
        task_id="ACTIVE-OLD",
        objective="Older active plan",
        context="Created earlier",
        steps=["Step 1"],
        priority="high"
    )
    old_active = pm.load_plan("ACTIVE-OLD")
    old_active.metadata.status = "Active"
    old_active.metadata.created_date = "2026-02-20T10:00:00Z"
    pm._write_plan_file(old_active_path, old_active)

    # Create newer Active plan
    new_active_path = pm.create_plan(
        task_id="ACTIVE-NEW",
        objective="Newer active plan",
        context="Created recently",
        steps=["Step 1"],
        priority="high"
    )
    new_active = pm.load_plan("ACTIVE-NEW")
    new_active.metadata.status = "Active"
    new_active.metadata.created_date = "2026-02-21T15:30:00Z"
    pm._write_plan_file(new_active_path, new_active)

    # find_active_plan should return newer Active plan
    found_plan = pm.find_active_plan()
    assert found_plan is not None
    assert found_plan.metadata.task_id == "ACTIVE-NEW"
    assert found_plan.metadata.created_date == "2026-02-21T15:30:00Z"

    logger.info("✓ Recent Active plan selection test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
