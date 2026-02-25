"""
E2E Integration Test: Multi-Session Workflow (T069)

Full-loop simulation across 4 simulated sessions:

Session 1: Create plan, complete steps 1-2, end session.
Session 2: Agent starts, scans /Plans/, resumes from step 3, completes 3-4,
           hits HITL gate, drafts approval, ends session.
Session 3: Plan still loaded, awaiting approval. Human approves mid-session-gap.
Session 4: Approval detected, execution continues, plan completed.

Verifies:
  - Reconciliation-First startup finds the correct active plan each session.
  - Plan resumes from the correct checkpoint (last completed step).
  - HITL gate persists approval wait across session boundaries.
  - Final plan is archived after all steps complete.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from agents.skills.managing_obsidian_vault.plan_manager import PlanManager
from agents.skills.managing_obsidian_vault.approval_manager import ApprovalManager, ApprovalStatus
from agents.skills.managing_obsidian_vault.audit_logger import AuditLogger


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def vault(tmp_path: Path) -> Path:
    for folder in [
        "Plans", "Done/Plans", "Done/Actions",
        "Pending_Approval", "Approved", "Rejected", "Logs",
    ]:
        (tmp_path / folder).mkdir(parents=True)
    (tmp_path / "Dashboard.md").write_text("# Dashboard\n\n## Current Mission\n\nNone\n")
    return tmp_path


PLAN_ID = "2026-e2e-multi-session"
STEPS = [
    "Research client requirements",
    "Draft project proposal document",
    "Create project timeline in vault",
    "✋ Send proposal to client@example.com for approval",
    "Log project kickoff in CRM",
]


def make_managers(vault: Path) -> tuple[PlanManager, ApprovalManager, AuditLogger]:
    return (
        PlanManager(vault_root=vault),
        ApprovalManager(vault_root=vault),
        AuditLogger(vault_root=vault),
    )


# ---------------------------------------------------------------------------
# T069: Multi-session workflow tests
# ---------------------------------------------------------------------------

class TestMultiSessionWorkflow:
    """E2E: Multi-session plan — interrupted and resumed across 4 sessions."""

    def test_session1_plan_created_steps_1_2_complete(self, vault: Path):
        """Session 1: Plan created, steps 1-2 completed, session ends."""
        plan_mgr, _, audit = make_managers(vault)

        plan_mgr.create_plan(
            task_id=PLAN_ID,
            objective="Onboard Client B and send project proposal",
            context="Client B agreed to scope. Proposal must be sent by Friday.",
            steps=STEPS,
            priority="medium",
        )
        audit.plan_created(PLAN_ID, "Onboard Client B")

        for step_num in [1, 2]:
            plan_mgr.update_step(
                plan_id=PLAN_ID,
                step_number=step_num,
                completed=True,
                log_entry=f"Step {step_num} completed in Session 1",
            )
            audit.step_completed(PLAN_ID, step_num, STEPS[step_num - 1])

        # Verify checkpoint
        plan = plan_mgr.load_plan(PLAN_ID)
        assert plan.steps[0].completed is True
        assert plan.steps[1].completed is True
        assert plan.steps[2].completed is False  # Session 1 ended before step 3

    def test_session2_reconciliation_resumes_from_step3(self, vault: Path):
        """Session 2: Reconciliation-First startup finds plan and resumes at step 3."""
        plan_mgr, approval_mgr, audit = make_managers(vault)

        # Setup: Session 1 state (steps 1-2 done)
        plan_mgr.create_plan(
            task_id=PLAN_ID,
            objective="Onboard Client B",
            context="Session resumption test",
            steps=STEPS,
        )
        plan_mgr.update_step(PLAN_ID, 1, completed=True, log_entry="Step 1 done")
        plan_mgr.update_step(PLAN_ID, 2, completed=True, log_entry="Step 2 done")

        # Session 2: Reconciliation-First
        active_plan = plan_mgr.find_active_plan()
        assert active_plan is not None, "find_active_plan() must find the active plan"
        assert active_plan.metadata.task_id == PLAN_ID
        assert active_plan.metadata.status != "Done"

        # Verify checkpoint: next incomplete step is 3
        next_step = active_plan.get_next_incomplete_step()
        assert next_step is not None
        assert next_step.number == 3

        # Session 2 continues: complete step 3
        plan_mgr.update_step(PLAN_ID, 3, completed=True, log_entry="Step 3 done in Session 2")

        # Reach step 4 (HITL) — draft approval and halt
        approval_path = approval_mgr.draft_external_action(
            action_type="email",
            target_recipient="client@example.com",
            plan_id=PLAN_ID,
            step_id=4,
            draft_content="Dear Client B, please find attached the project proposal...",
            rationale="Step 4 requires sending proposal email",
            step_description=STEPS[3].replace("✋ ", ""),
        )
        audit.approval_drafted(PLAN_ID, 4, "email", approval_path.name)

        assert approval_path.exists()

    def test_session3_plan_remains_blocked_awaiting_approval(self, vault: Path):
        """Session 3: Plan is still blocked — approval not yet given."""
        plan_mgr, approval_mgr, _ = make_managers(vault)

        # Setup: Session 2 state (steps 1-3 done, step 4 pending approval)
        plan_mgr.create_plan(
            task_id=PLAN_ID,
            objective="Onboard Client B",
            context="Session 3 test",
            steps=STEPS,
        )
        for i in range(1, 4):
            plan_mgr.update_step(PLAN_ID, i, completed=True)

        approval_path = approval_mgr.draft_external_action(
            action_type="email",
            target_recipient="client@example.com",
            plan_id=PLAN_ID,
            step_id=4,
            draft_content="Proposal body",
            rationale="Step 4",
            step_description="Send proposal",
        )

        # Session 3 reconciliation
        active_plan = plan_mgr.find_active_plan()
        assert active_plan is not None

        # Verify: approval file still in /Pending_Approval/
        pending_files = list((vault / "Pending_Approval").glob("*.md"))
        assert len(pending_files) == 1, "Approval file must still be pending"

        # Verify: plan cannot proceed (HITL step not yet approved)
        with pytest.raises(PermissionError):
            plan_mgr.validate_hitl_completion(
                plan_id=PLAN_ID,
                step_number=4,
                approval_manager=None,
            )

    def test_session4_approval_detected_execution_completes(self, vault: Path):
        """Session 4: Human approved — execution continues and plan completes."""
        plan_mgr, approval_mgr, audit = make_managers(vault)
        mock_mcp = MagicMock(return_value="Email sent. message_id=multi-session-test")

        # Setup: steps 1-3 done, approval drafted
        plan_mgr.create_plan(
            task_id=PLAN_ID,
            objective="Onboard Client B",
            context="Session 4 test",
            steps=STEPS,
        )
        for i in range(1, 4):
            plan_mgr.update_step(PLAN_ID, i, completed=True)

        approval_path = approval_mgr.draft_external_action(
            action_type="email",
            target_recipient="client@example.com",
            plan_id=PLAN_ID,
            step_id=4,
            draft_content="Proposal body",
            rationale="Step 4",
            step_description="Send proposal email",
        )

        # Simulate human approval between sessions
        approved_path = vault / "Approved" / approval_path.name
        approved_path.write_text(approval_path.read_text())
        approval_path.unlink()

        # Session 4: agent detects approval
        approval_status = approval_mgr.detect_approval_status(approval_path.name)
        assert approval_status == ApprovalStatus.APPROVED

        # Execute
        success, msg = approval_mgr.execute_approved_action(
            filename=approval_path.name,
            mcp_dispatcher=mock_mcp,
        )
        assert success is True
        audit.approval_executed(PLAN_ID, 4, "email", approval_path.name)

        # Complete step 4 in plan
        plan_mgr.update_step(PLAN_ID, 4, completed=True, log_entry="Email sent via MCP")

        # Complete step 5
        plan_mgr.update_step(PLAN_ID, 5, completed=True, log_entry="CRM logged")

        # Archive plan
        archived = plan_mgr.archive_plan(PLAN_ID)
        audit.plan_archived(PLAN_ID)

        assert archived.exists()
        assert not (vault / "Plans" / f"PLAN-{PLAN_ID}.md").exists()

        # No more active plans
        next_plan = plan_mgr.find_active_plan()
        assert next_plan is None

    def test_full_multi_session_sequence(self, vault: Path):
        """Integration: Full 4-session sequence runs end-to-end without errors."""
        plan_mgr, approval_mgr, audit = make_managers(vault)
        mock_mcp = MagicMock(return_value="OK")

        # --- Session 1 ---
        plan_mgr.create_plan(
            task_id=PLAN_ID,
            objective="Onboard Client B",
            context="Full sequence test",
            steps=STEPS,
        )
        plan_mgr.update_step(PLAN_ID, 1, completed=True)
        plan_mgr.update_step(PLAN_ID, 2, completed=True)

        # --- Session 2 ---
        assert plan_mgr.find_active_plan() is not None
        plan_mgr.update_step(PLAN_ID, 3, completed=True)

        approval_path = approval_mgr.draft_external_action(
            action_type="email",
            target_recipient="client@example.com",
            plan_id=PLAN_ID,
            step_id=4,
            draft_content="Proposal",
            rationale="Step 4",
            step_description="Send proposal",
        )

        # --- Session 3 (human approves) ---
        approved_path = vault / "Approved" / approval_path.name
        approved_path.write_text(approval_path.read_text())
        approval_path.unlink()

        # --- Session 4 ---
        assert plan_mgr.find_active_plan() is not None
        approval_mgr.execute_approved_action(approval_path.name, mcp_dispatcher=mock_mcp)
        plan_mgr.update_step(PLAN_ID, 4, completed=True)
        plan_mgr.update_step(PLAN_ID, 5, completed=True)
        plan_mgr.archive_plan(PLAN_ID)

        assert plan_mgr.find_active_plan() is None
        assert (vault / "Done" / "Plans" / f"PLAN-{PLAN_ID}.md").exists()
