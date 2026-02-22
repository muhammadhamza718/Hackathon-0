"""
Test: Plan prioritization (T033)

Tests that find_active_plan() correctly prioritizes plans by status (Active > Blocked > Draft)
and by creation date (most recent first).

Setup: Create 3 plans (Draft, Active, Blocked) with different timestamps
Trigger: Session start (call find_active_plan())
Assert: Active plan loaded (highest priority)
Assert: If multiple Active: Most recent loaded
"""

import logging
import pytest
from pathlib import Path
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


def test_plan_prioritization_status_first(vault_tmp):
    """
    Test that Active plans take priority over Blocked and Draft.

    Create plans with different statuses, verify Active is selected.
    """
    pm = PlanManager(vault_tmp)

    # Create Draft plan (low priority, newest timestamp)
    draft_path = pm.create_plan(
        task_id="DRAFT-RECENT",
        objective="Recent draft plan",
        context="Created most recently but Draft status",
        steps=["Step 1", "Step 2"],
        priority="medium"
    )
    draft = pm.load_plan("DRAFT-RECENT")
    draft.metadata.status = "Draft"
    draft.metadata.created_date = "2026-02-21T18:00:00Z"  # Most recent
    pm._write_plan_file(draft_path, draft)

    # Create Blocked plan (medium priority, older)
    blocked_path = pm.create_plan(
        task_id="BLOCKED-OLD",
        objective="Older blocked plan",
        context="Blocked but older than draft",
        steps=["Step 1"],
        priority="high"
    )
    blocked = pm.load_plan("BLOCKED-OLD")
    blocked.metadata.status = "Blocked"
    blocked.metadata.blocked_reason = "Awaiting approval"
    blocked.metadata.created_date = "2026-02-21T12:00:00Z"
    pm._write_plan_file(blocked_path, blocked)

    # Create Active plan (highest priority, middle timestamp)
    active_path = pm.create_plan(
        task_id="ACTIVE-MID",
        objective="Middle-dated active plan",
        context="Active but not newest",
        steps=["Step 1", "Step 2", "Step 3"],
        priority="high"
    )
    active = pm.load_plan("ACTIVE-MID")
    active.metadata.status = "Active"
    active.metadata.created_date = "2026-02-21T15:00:00Z"
    pm._write_plan_file(active_path, active)

    # find_active_plan should return Active plan regardless of timestamp
    found = pm.find_active_plan()
    assert found is not None
    assert found.metadata.task_id == "ACTIVE-MID"
    assert found.metadata.status == "Active"

    logger.info("✓ Status prioritization (Active > Blocked > Draft) verified")


def test_plan_prioritization_blocked_over_draft(vault_tmp):
    """
    Test that Blocked plans take priority over Draft.

    Create Blocked and Draft plans with different timestamps,
    verify Blocked is selected (even if Draft is newer).
    """
    pm = PlanManager(vault_tmp)

    # Create Draft plan (oldest priority, newest timestamp)
    draft_path = pm.create_plan(
        task_id="DRAFT-NEWEST",
        objective="Newest draft plan",
        context="Draft but created most recently",
        steps=["Step 1"],
        priority="low"
    )
    draft = pm.load_plan("DRAFT-NEWEST")
    draft.metadata.status = "Draft"
    draft.metadata.created_date = "2026-02-21T18:00:00Z"  # Most recent
    pm._write_plan_file(draft_path, draft)

    # Create Blocked plan (higher priority, older)
    blocked_path = pm.create_plan(
        task_id="BLOCKED-OLDEST",
        objective="Oldest blocked plan",
        context="Blocked and older",
        steps=["Step 1"],
        priority="high"
    )
    blocked = pm.load_plan("BLOCKED-OLDEST")
    blocked.metadata.status = "Blocked"
    blocked.metadata.blocked_reason = "Awaiting human decision"
    blocked.metadata.created_date = "2026-02-21T10:00:00Z"  # Oldest
    pm._write_plan_file(blocked_path, blocked)

    # find_active_plan should return Blocked plan despite Draft being newer
    found = pm.find_active_plan()
    assert found is not None
    assert found.metadata.task_id == "BLOCKED-OLDEST"
    assert found.metadata.status == "Blocked"

    logger.info("✓ Status prioritization (Blocked > Draft) verified")


def test_multiple_blocked_plans_recent_first(vault_tmp):
    """
    Test that when multiple Blocked plans exist, most recent is selected.

    Create 2 Blocked plans, verify most recent is returned.
    """
    pm = PlanManager(vault_tmp)

    # Create older Blocked plan
    old_blocked_path = pm.create_plan(
        task_id="BLOCKED-OLDER",
        objective="Older blocked plan",
        context="Created earlier",
        steps=["Step 1"],
        priority="medium"
    )
    old_blocked = pm.load_plan("BLOCKED-OLDER")
    old_blocked.metadata.status = "Blocked"
    old_blocked.metadata.blocked_reason = "Pending approval"
    old_blocked.metadata.created_date = "2026-02-20T10:00:00Z"
    pm._write_plan_file(old_blocked_path, old_blocked)

    # Create newer Blocked plan
    new_blocked_path = pm.create_plan(
        task_id="BLOCKED-NEWER",
        objective="Newer blocked plan",
        context="Created recently",
        steps=["Step 1"],
        priority="medium"
    )
    new_blocked = pm.load_plan("BLOCKED-NEWER")
    new_blocked.metadata.status = "Blocked"
    new_blocked.metadata.blocked_reason = "Awaiting review"
    new_blocked.metadata.created_date = "2026-02-21T14:30:00Z"
    pm._write_plan_file(new_blocked_path, new_blocked)

    # find_active_plan should return newer Blocked plan
    found = pm.find_active_plan()
    assert found is not None
    assert found.metadata.task_id == "BLOCKED-NEWER"
    assert found.metadata.created_date == "2026-02-21T14:30:00Z"

    logger.info("✓ Recent Blocked plan selection verified")


def test_multiple_active_plans_recent_first(vault_tmp):
    """
    Test that when multiple Active plans exist, most recent is selected.

    Create 2 Active plans with different timestamps,
    verify most recent Active is returned.
    """
    pm = PlanManager(vault_tmp)

    # Create older Active plan
    old_active_path = pm.create_plan(
        task_id="ACTIVE-OLDER",
        objective="Older active plan",
        context="Created yesterday",
        steps=["Step 1", "Step 2"],
        priority="high"
    )
    old_active = pm.load_plan("ACTIVE-OLDER")
    old_active.metadata.status = "Active"
    old_active.metadata.created_date = "2026-02-20T09:00:00Z"
    pm._write_plan_file(old_active_path, old_active)

    # Create newer Active plan
    new_active_path = pm.create_plan(
        task_id="ACTIVE-NEWER",
        objective="Newer active plan",
        context="Created today",
        steps=["Step 1", "Step 2", "Step 3"],
        priority="high"
    )
    new_active = pm.load_plan("ACTIVE-NEWER")
    new_active.metadata.status = "Active"
    new_active.metadata.created_date = "2026-02-21T16:45:00Z"
    pm._write_plan_file(new_active_path, new_active)

    # find_active_plan should return newer Active plan
    found = pm.find_active_plan()
    assert found is not None
    assert found.metadata.task_id == "ACTIVE-NEWER"
    assert found.metadata.created_date == "2026-02-21T16:45:00Z"

    logger.info("✓ Recent Active plan selection verified")


def test_no_done_plans_returned(vault_tmp):
    """
    Test that Done plans are never returned by find_active_plan().

    Create a Done plan and an Active plan,
    verify only Active is returned.
    """
    pm = PlanManager(vault_tmp)

    # Create and archive a Done plan
    done_plan_path = pm.create_plan(
        task_id="DONE-RECENT",
        objective="Recently completed plan",
        context="This plan is done",
        steps=["Step 1"],
        priority="low"
    )
    done = pm.load_plan("DONE-RECENT")
    done.metadata.status = "Done"
    done.metadata.created_date = "2026-02-21T17:00:00Z"  # Most recent
    pm._write_plan_file(done_plan_path, done)

    # Create Active plan (older than Done)
    active_path = pm.create_plan(
        task_id="ACTIVE-OLD",
        objective="Older active plan",
        context="Still active",
        steps=["Step 1"],
        priority="high"
    )
    active = pm.load_plan("ACTIVE-OLD")
    active.metadata.status = "Active"
    active.metadata.created_date = "2026-02-21T10:00:00Z"  # Older but Active
    pm._write_plan_file(active_path, active)

    # find_active_plan should return Active plan, not Done
    found = pm.find_active_plan()
    assert found is not None
    assert found.metadata.task_id == "ACTIVE-OLD"
    assert found.metadata.status == "Active"

    logger.info("✓ Done plans correctly excluded from resumption")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
