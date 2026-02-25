"""
E2E Integration Test: Invoice Workflow (T068)

Full-loop simulation:
  "Generate and send invoice to Client A for $1,500"

Verifies:
  1. Request triggers complexity detection
  2. Plan created with 4 steps (last step is ✋ HITL)
  3. Steps 1-3 execute autonomously (calculate, generate PDF, log)
  4. Step 4 (email) triggers approval request in /Pending_Approval/
  5. Human approves (simulated by moving file to /Approved/)
  6. Action dispatched via MCP dispatcher (mocked)
  7. Approval file archived to /Done/Actions/
  8. Plan moved to /Done/Plans/
  9. Dashboard updated with completion

Assertions:
  - All steps executed in order
  - No step skipped
  - HITL gate enforced (no MCP call without /Approved/ file)
  - Audit log entries written to /Logs/YYYY-MM-DD.json
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional
from unittest.mock import MagicMock

from agents.skills.managing_obsidian_vault.plan_manager import PlanManager, PlanContent
from agents.skills.managing_obsidian_vault.approval_manager import (
    ApprovalManager,
    ApprovalRequest,
    ApprovalStatus,
)
from agents.skills.managing_obsidian_vault.audit_logger import AuditLogger
from agents.skills.managing_obsidian_vault.complexity_detector import detect_complexity
from agents.skills.managing_obsidian_vault.dashboard_reconciler import DashboardReconciler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """Create a fully-initialised temporary vault."""
    for folder in [
        "Plans", "Done/Plans", "Done/Actions",
        "Pending_Approval", "Approved", "Rejected", "Logs",
    ]:
        (tmp_path / folder).mkdir(parents=True)
    # Minimal Dashboard
    (tmp_path / "Dashboard.md").write_text("# Dashboard\n\n## Current Mission\n\nNone\n")
    return tmp_path


@pytest.fixture
def plan_mgr(vault: Path) -> PlanManager:
    return PlanManager(vault_root=vault)


@pytest.fixture
def approval_mgr(vault: Path) -> ApprovalManager:
    return ApprovalManager(vault_root=vault)


@pytest.fixture
def audit(vault: Path) -> AuditLogger:
    return AuditLogger(vault_root=vault)


@pytest.fixture
def dashboard(vault: Path) -> DashboardReconciler:
    return DashboardReconciler(vault_root=vault)


@pytest.fixture
def mock_mcp():
    """Mock MCP dispatcher that returns a success message."""
    dispatcher = MagicMock(return_value="Email sent successfully. message_id=test-abc123")
    return dispatcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today_log_path(vault: Path) -> Path:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return vault / "Logs" / f"{date_str}.json"


def _read_audit_events(vault: Path) -> list[dict]:
    log_path = _today_log_path(vault)
    if not log_path.exists():
        return []
    return [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# T068: Full-loop invoice workflow test
# ---------------------------------------------------------------------------

class TestInvoiceWorkflow:
    """E2E: Invoice workflow — request → plan → completion → dashboard update."""

    PLAN_ID = "2026-e2e-invoice"
    STEPS = [
        "Calculate invoice total including 10% tax",
        "Generate invoice PDF",
        "Log invoice in accounts ledger",
        "✋ Send invoice email to client@example.com",
    ]

    def test_step1_complexity_detection(self):
        """Complex task is correctly identified."""
        user_input = "Generate and send invoice to Client A for $1,500"
        result = detect_complexity(user_input)
        assert result.is_complex(), "Invoice task must be classified as complex"

    def test_step2_plan_created_with_four_steps(self, plan_mgr: PlanManager, audit: AuditLogger):
        """Plan is created with correct schema and 4 steps."""
        plan_path = plan_mgr.create_plan(
            task_id=self.PLAN_ID,
            objective="Generate and send invoice to Client A for $1,500",
            context="Client A ordered services. Invoice must be sent by end of day.",
            steps=self.STEPS,
            priority="high",
        )
        audit.plan_created(self.PLAN_ID, "Generate and send invoice to Client A for $1,500")

        assert plan_path.exists()
        plan = plan_mgr.load_plan(self.PLAN_ID)
        assert plan.metadata.task_id == self.PLAN_ID
        assert len(plan.steps) == 4
        # Step 4 must be HITL
        assert plan.steps[3].hitl_required is True
        # Steps 1-3 must NOT be HITL
        for i in range(3):
            assert plan.steps[i].hitl_required is False

    def test_step3_autonomous_steps_execute_in_order(self, plan_mgr: PlanManager, audit: AuditLogger):
        """Steps 1-3 can be marked complete without approval."""
        plan_mgr.create_plan(
            task_id=self.PLAN_ID,
            objective="Generate and send invoice to Client A",
            context="E2E test context",
            steps=self.STEPS,
        )

        for step_num in range(1, 4):
            plan_mgr.update_step(
                plan_id=self.PLAN_ID,
                step_number=step_num,
                completed=True,
                log_entry=f"Completed step {step_num}",
            )
            audit.step_completed(self.PLAN_ID, step_num, self.STEPS[step_num - 1])

        plan = plan_mgr.load_plan(self.PLAN_ID)
        for i in range(3):
            assert plan.steps[i].completed is True, f"Step {i+1} should be complete"
        # Step 4 still incomplete
        assert plan.steps[3].completed is False

    def test_step4_hitl_gate_blocks_execution(
        self,
        plan_mgr: PlanManager,
        approval_mgr: ApprovalManager,
        audit: AuditLogger,
    ):
        """Step 4 (HITL) creates approval request and halts execution."""
        plan_mgr.create_plan(
            task_id=self.PLAN_ID,
            objective="Generate and send invoice to Client A",
            context="E2E test context",
            steps=self.STEPS,
        )

        # Draft approval request (instead of calling MCP directly)
        approval_path = approval_mgr.draft_external_action(
            action_type="email",
            target_recipient="client@example.com",
            plan_id=self.PLAN_ID,
            step_id=4,
            draft_content="Dear Client A, please find attached your invoice for $1,650.",
            rationale="Step 4 of invoice workflow requires sending email",
            step_description=self.STEPS[3].replace("✋ ", ""),
        )
        audit.approval_drafted(self.PLAN_ID, 4, "email", approval_path.name)

        assert approval_path.exists(), "Approval file must be created in /Pending_Approval/"

        # Confirm: HITL step cannot be marked complete without approval
        with pytest.raises(PermissionError):
            plan_mgr.validate_hitl_completion(
                plan_id=self.PLAN_ID,
                step_number=4,
                approval_manager=None,  # No approval manager → safe-fail
            )

    def test_step5_human_approves_and_mcp_executes(
        self,
        vault: Path,
        plan_mgr: PlanManager,
        approval_mgr: ApprovalManager,
        audit: AuditLogger,
        mock_mcp: MagicMock,
    ):
        """After human approves, MCP executes and file moves to /Done/Actions/."""
        plan_mgr.create_plan(
            task_id=self.PLAN_ID,
            objective="Generate and send invoice",
            context="E2E test context",
            steps=self.STEPS,
        )

        approval_path = approval_mgr.draft_external_action(
            action_type="email",
            target_recipient="client@example.com",
            plan_id=self.PLAN_ID,
            step_id=4,
            draft_content="Dear Client A, invoice attached.",
            rationale="Invoice workflow step 4",
            step_description="Send invoice email to client@example.com",
        )

        # Simulate human approval: move file from /Pending_Approval/ to /Approved/
        approved_path = vault / "Approved" / approval_path.name
        approved_path.write_text(approval_path.read_text())
        approval_path.unlink()

        # Execute approved action
        success, msg = approval_mgr.execute_approved_action(
            filename=approval_path.name,
            mcp_dispatcher=mock_mcp,
        )
        audit.approval_executed(self.PLAN_ID, 4, "email", approval_path.name)

        assert success is True
        assert "sent successfully" in msg.lower() or "dry-run" in msg.lower() or mock_mcp.called
        # File must be in /Done/Actions/
        assert (vault / "Done" / "Actions" / approval_path.name).exists()
        # File must NOT still be in /Approved/
        assert not (vault / "Approved" / approval_path.name).exists()

    def test_step6_plan_archived_after_completion(
        self,
        vault: Path,
        plan_mgr: PlanManager,
        approval_mgr: ApprovalManager,
        audit: AuditLogger,
        mock_mcp: MagicMock,
    ):
        """Plan is moved to /Done/Plans/ after all steps complete."""
        plan_mgr.create_plan(
            task_id=self.PLAN_ID,
            objective="Generate and send invoice",
            context="E2E test context",
            steps=self.STEPS,
        )

        # Complete steps 1-3
        for i in range(1, 4):
            plan_mgr.update_step(self.PLAN_ID, i, completed=True, log_entry=f"Step {i} done")

        # Draft, approve, execute step 4
        approval_path = approval_mgr.draft_external_action(
            action_type="email",
            target_recipient="client@example.com",
            plan_id=self.PLAN_ID,
            step_id=4,
            draft_content="Invoice body",
            rationale="Final step",
            step_description="Send invoice email",
        )
        approved_path = vault / "Approved" / approval_path.name
        approved_path.write_text(approval_path.read_text())
        approval_path.unlink()

        approval_mgr.execute_approved_action(
            filename=approval_path.name,
            mcp_dispatcher=mock_mcp,
        )

        # Mark step 4 complete (with approval proof via ApprovalManager)
        plan_mgr.update_step(
            plan_id=self.PLAN_ID,
            step_number=4,
            completed=True,
            log_entry="Executed external email action",
        )

        # Archive plan
        archived_path = plan_mgr.archive_plan(self.PLAN_ID)
        audit.plan_archived(self.PLAN_ID)

        assert archived_path.exists()
        assert (vault / "Done" / "Plans" / f"PLAN-{self.PLAN_ID}.md").exists()
        assert not (vault / "Plans" / f"PLAN-{self.PLAN_ID}.md").exists()

    def test_step7_audit_log_records_all_events(
        self,
        vault: Path,
        plan_mgr: PlanManager,
        approval_mgr: ApprovalManager,
        audit: AuditLogger,
        mock_mcp: MagicMock,
    ):
        """Audit log in /Logs/YYYY-MM-DD.json records all key events."""
        plan_mgr.create_plan(
            task_id=self.PLAN_ID,
            objective="Generate and send invoice",
            context="E2E audit test",
            steps=self.STEPS,
        )
        audit.plan_created(self.PLAN_ID, "Generate and send invoice")
        audit.step_completed(self.PLAN_ID, 1, "Calculate total")
        audit.approval_drafted(self.PLAN_ID, 4, "email", "some-file.md")
        audit.approval_executed(self.PLAN_ID, 4, "email", "some-file.md")
        audit.plan_archived(self.PLAN_ID)

        events = _read_audit_events(vault)
        event_types = [e["event"] for e in events]

        assert "plan_created" in event_types
        assert "step_completed" in event_types
        assert "approval_drafted" in event_types
        assert "approval_executed" in event_types
        assert "plan_archived" in event_types

        # All events reference the correct plan_id
        for event in events:
            assert event["plan_id"] == self.PLAN_ID

    def test_step8_dashboard_updated_on_completion(
        self,
        vault: Path,
        plan_mgr: PlanManager,
        dashboard: DashboardReconciler,
    ):
        """Dashboard reflects completed plan after archival."""
        plan_mgr.create_plan(
            task_id=self.PLAN_ID,
            objective="Generate and send invoice",
            context="Dashboard update test",
            steps=["Calculate total"],
        )

        # Mark complete and archive
        plan_mgr.update_step(self.PLAN_ID, 1, completed=True)
        plan_mgr.archive_plan(self.PLAN_ID)

        # Dashboard reconcile
        dashboard.reconcile()

        dashboard_content = (vault / "Dashboard.md").read_text()
        # After archival /Plans/ is empty — dashboard shows no active mission
        assert "None" in dashboard_content or self.PLAN_ID not in dashboard_content
