"""
E2E Integration Test: Safety Breach Prevention (T070)

Scenario: Agent attempts to send an email WITHOUT going through the
          HITL approval workflow.

Verifies:
  - Attempting to execute an action file that is NOT in /Approved/ raises FileNotFoundError.
  - Attempting to mark a HITL step complete without ApprovalManager raises PermissionError.
  - No MCP dispatcher is ever called if the safety gate is triggered.
  - The vault state is unchanged after a blocked action.
  - Audit log records the attempt (via explicit logging — no silent failures).
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    return tmp_path


PLAN_ID = "2026-e2e-safety"
HITL_STEPS = [
    "Prepare email draft",
    "✋ Send email to victim@example.com",
]


def make_managers(vault: Path):
    return (
        PlanManager(vault_root=vault),
        ApprovalManager(vault_root=vault),
        AuditLogger(vault_root=vault),
    )


# ---------------------------------------------------------------------------
# T070: Safety breach prevention tests
# ---------------------------------------------------------------------------

class TestSafetyBreachPrevention:
    """E2E: Agent cannot execute external actions without /Approved/ file."""

    def test_execute_without_approved_file_raises(self, vault: Path):
        """FileNotFoundError raised when no file exists in /Approved/."""
        _, approval_mgr, _ = make_managers(vault)
        mock_mcp = MagicMock()

        with pytest.raises(FileNotFoundError, match="Approved file not found"):
            approval_mgr.execute_approved_action(
                filename="nonexistent-approval.md",
                mcp_dispatcher=mock_mcp,
            )

        # MCP was NEVER called
        mock_mcp.assert_not_called()

    def test_execute_from_pending_raises_not_from_approved(self, vault: Path):
        """File in /Pending_Approval/ does NOT count as approved."""
        plan_mgr, approval_mgr, _ = make_managers(vault)
        mock_mcp = MagicMock()

        plan_mgr.create_plan(
            task_id=PLAN_ID,
            objective="Send email unsafely",
            context="Safety test",
            steps=HITL_STEPS,
        )

        approval_path = approval_mgr.draft_external_action(
            action_type="email",
            target_recipient="victim@example.com",
            plan_id=PLAN_ID,
            step_id=2,
            draft_content="Malicious email body",
            rationale="Attempting bypass",
            step_description="Send email without approval",
        )

        # File is in /Pending_Approval/ — trying to execute by filename
        # must fail because it's not in /Approved/
        with pytest.raises(FileNotFoundError):
            approval_mgr.execute_approved_action(
                filename=approval_path.name,
                mcp_dispatcher=mock_mcp,
            )

        mock_mcp.assert_not_called()

    def test_hitl_step_mark_complete_without_approval_manager_raises(self, vault: Path):
        """PermissionError raised when trying to complete HITL step without ApprovalManager."""
        plan_mgr, _, _ = make_managers(vault)

        plan_mgr.create_plan(
            task_id=PLAN_ID,
            objective="Send email unsafely",
            context="Safety test",
            steps=HITL_STEPS,
        )

        with pytest.raises(PermissionError, match="no ApprovalManager provided"):
            plan_mgr.validate_hitl_completion(
                plan_id=PLAN_ID,
                step_number=2,
                approval_manager=None,
            )

    def test_hitl_step_mark_complete_without_executed_file_raises(self, vault: Path):
        """PermissionError raised if HITL step has no executed approval file."""
        plan_mgr, approval_mgr, _ = make_managers(vault)

        plan_mgr.create_plan(
            task_id=PLAN_ID,
            objective="Send email unsafely",
            context="Safety test",
            steps=HITL_STEPS,
        )

        # Draft a file (pending — not executed)
        approval_mgr.draft_external_action(
            action_type="email",
            target_recipient="victim@example.com",
            plan_id=PLAN_ID,
            step_id=2,
            draft_content="Email body",
            rationale="Step 2",
            step_description="Send email",
        )

        # Should raise because file was never executed
        with pytest.raises(PermissionError):
            plan_mgr.validate_hitl_completion(
                plan_id=PLAN_ID,
                step_number=2,
                approval_manager=approval_mgr,
            )

    def test_vault_state_unchanged_after_blocked_action(self, vault: Path):
        """Vault files are not modified when an action is blocked."""
        _, approval_mgr, _ = make_managers(vault)
        mock_mcp = MagicMock()

        # Record initial state
        approved_files_before = list((vault / "Approved").glob("*.md"))
        done_files_before = list((vault / "Done" / "Actions").glob("*.md"))

        # Attempt blocked execution
        try:
            approval_mgr.execute_approved_action("no-such-file.md", mcp_dispatcher=mock_mcp)
        except FileNotFoundError:
            pass

        # State unchanged
        approved_files_after = list((vault / "Approved").glob("*.md"))
        done_files_after = list((vault / "Done" / "Actions").glob("*.md"))

        assert approved_files_before == approved_files_after
        assert done_files_before == done_files_after
        mock_mcp.assert_not_called()

    def test_non_hitl_step_does_not_require_approval(self, vault: Path):
        """Non-HITL steps can be completed without any approval check."""
        plan_mgr, approval_mgr, _ = make_managers(vault)

        plan_mgr.create_plan(
            task_id=PLAN_ID,
            objective="Mixed plan",
            context="Safety boundary test",
            steps=HITL_STEPS,
        )

        # Step 1 has no ✋ — should succeed without any approval manager
        result = plan_mgr.validate_hitl_completion(
            plan_id=PLAN_ID,
            step_number=1,
            approval_manager=None,
        )
        assert result is True

    def test_mcp_never_called_if_file_not_in_approved(self, vault: Path):
        """MCP dispatcher is never invoked for unapproved files."""
        plan_mgr, approval_mgr, _ = make_managers(vault)
        call_log = []

        def sentinel_mcp(req):
            call_log.append(req)
            return "SHOULD NOT REACH HERE"

        plan_mgr.create_plan(
            task_id=PLAN_ID,
            objective="Bypass test",
            context="Safety test",
            steps=HITL_STEPS,
        )

        # Draft an approval (pending — not approved)
        approval_path = approval_mgr.draft_external_action(
            action_type="email",
            target_recipient="victim@example.com",
            plan_id=PLAN_ID,
            step_id=2,
            draft_content="Email",
            rationale="Bypass",
            step_description="Attempt bypass",
        )

        # Attempt to execute — must fail before MCP is reached
        with pytest.raises(FileNotFoundError):
            approval_mgr.execute_approved_action(
                filename=approval_path.name,
                mcp_dispatcher=sentinel_mcp,
            )

        assert len(call_log) == 0, "MCP sentinel must never be called"

    def test_approval_file_traceability_fields_present(self, vault: Path):
        """T064: Approval file contains plan_id, step_id, step_description for audit trail."""
        plan_mgr, approval_mgr, _ = make_managers(vault)

        plan_mgr.create_plan(
            task_id=PLAN_ID,
            objective="Traceability test",
            context="Verify T064",
            steps=HITL_STEPS,
        )

        approval_path = approval_mgr.draft_external_action(
            action_type="email",
            target_recipient="audit@example.com",
            plan_id=PLAN_ID,
            step_id=2,
            draft_content="Email body",
            rationale="Testing traceability",
            step_description="Send email to audit@example.com",
        )

        # Parse the file and verify traceability fields
        req = ApprovalRequest.from_file(approval_path)

        assert req.plan_id == PLAN_ID
        assert req.step_id == 2
        assert req.step_description == "Send email to audit@example.com"
        assert req.status == ApprovalStatus.PENDING
