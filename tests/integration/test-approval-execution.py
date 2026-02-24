"""
T041 — Integration test: Approval execution on file move to /Approved/.

Verifies that execute_approved_action:
  1. Reads the approval file from /Approved/
  2. Calls the MCP dispatcher (simulated via callable mock)
  3. Returns success=True with result message
  4. Moves file to /Done/Actions/ and removes from /Approved/
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agents.skills.managing_obsidian_vault.approval_manager import (
    ApprovalManager,
    ApprovalRequest,
    ApprovalStatus,
)


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    (tmp_path / "Pending_Approval").mkdir()
    (tmp_path / "Approved").mkdir()
    (tmp_path / "Rejected").mkdir()
    (tmp_path / "Done" / "Actions").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def manager(vault: Path) -> ApprovalManager:
    return ApprovalManager(vault_root=vault)


def _place_approval_file(vault: Path, folder: str, filename: str) -> Path:
    """Helper: write a valid approval file into a folder."""
    content = (
        "---\n"
        "action_type: email\n"
        "target_recipient: client@example.com\n"
        "plan_id: PLAN-2026-001\n"
        "step_id: 4\n"
        "rationale: Send invoice to Client A\n"
        "created_date: '2026-02-24T10:00:00Z'\n"
        "status: pending\n"
        "---\n\n"
        "# Email Approval Request\n\n"
        "**To / Target**: client@example.com\n\n"
        "Dear Client A, invoice attached.\n\n"
        "> Move to /Approved/ to execute or /Rejected/ to deny.\n"
    )
    path = vault / folder / filename
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Test 1: Successful execution moves file to /Done/Actions/
# ---------------------------------------------------------------------------

def test_execution_archives_file_to_done(manager: ApprovalManager, vault: Path):
    """On success, approved file must move to /Done/Actions/."""
    filename = "2026-02-24T10-00-00Z_email_client.md"
    _place_approval_file(vault, "Approved", filename)

    dispatcher = MagicMock(return_value="Email sent successfully")
    success, msg = manager.execute_approved_action(filename, mcp_dispatcher=dispatcher)

    assert success is True
    assert "Email sent successfully" in msg

    # File moved to Done/Actions
    assert (vault / "Done" / "Actions" / filename).exists()
    # File removed from Approved
    assert not (vault / "Approved" / filename).exists()


# ---------------------------------------------------------------------------
# Test 2: MCP dispatcher is actually called with the right action type
# ---------------------------------------------------------------------------

def test_mcp_dispatcher_called_with_request(manager: ApprovalManager, vault: Path):
    """MCP dispatcher must receive an ApprovalRequest object."""
    filename = "2026-02-24T10-00-00Z_email_client.md"
    _place_approval_file(vault, "Approved", filename)

    dispatched_requests = []

    def capturing_dispatcher(req: ApprovalRequest) -> str:
        dispatched_requests.append(req)
        return "dispatched"

    manager.execute_approved_action(filename, mcp_dispatcher=capturing_dispatcher)

    assert len(dispatched_requests) == 1
    req = dispatched_requests[0]
    assert req.action_type == "email"
    assert req.target_recipient == "client@example.com"
    assert req.plan_id == "PLAN-2026-001"
    assert req.step_id == 4


# ---------------------------------------------------------------------------
# Test 3: Dry-run succeeds when no dispatcher provided
# ---------------------------------------------------------------------------

def test_dry_run_succeeds_without_dispatcher(manager: ApprovalManager, vault: Path):
    """Without a dispatcher, execution succeeds in dry-run mode."""
    filename = "2026-02-24T10-00-00Z_email_client.md"
    _place_approval_file(vault, "Approved", filename)

    success, msg = manager.execute_approved_action(filename, mcp_dispatcher=None)

    assert success is True
    assert "DRY-RUN" in msg


# ---------------------------------------------------------------------------
# Test 4: MCP failure returns file to /Pending_Approval/
# ---------------------------------------------------------------------------

def test_mcp_failure_returns_file_to_pending(manager: ApprovalManager, vault: Path):
    """On MCP failure, file must be returned to /Pending_Approval/."""
    filename = "2026-02-24T10-00-00Z_email_client.md"
    _place_approval_file(vault, "Approved", filename)

    def failing_dispatcher(req: ApprovalRequest) -> str:
        raise ConnectionError("SMTP server unreachable")

    success, msg = manager.execute_approved_action(filename, mcp_dispatcher=failing_dispatcher)

    assert success is False
    assert "SMTP server unreachable" in msg

    # File returned to /Pending_Approval/
    assert (vault / "Pending_Approval" / filename).exists()
    # Not in Done/Actions
    assert not (vault / "Done" / "Actions" / filename).exists()


# ---------------------------------------------------------------------------
# Test 5: Executed file has status=executed in Done/Actions/
# ---------------------------------------------------------------------------

def test_executed_file_status_updated(manager: ApprovalManager, vault: Path):
    """Archived file must have status=executed in its YAML."""
    filename = "2026-02-24T10-00-00Z_email_client.md"
    _place_approval_file(vault, "Approved", filename)

    manager.execute_approved_action(
        filename, mcp_dispatcher=lambda r: "OK"
    )

    done_path = vault / "Done" / "Actions" / filename
    req = ApprovalRequest.from_file(done_path)
    assert req.status == ApprovalStatus.EXECUTED
