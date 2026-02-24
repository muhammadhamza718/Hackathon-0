"""
T040 — Integration test: Approval request file creation.

Verifies that DraftExternalAction (via ApprovalManager.draft_external_action):
  1. Creates a file in /Pending_Approval/ with the correct name format
  2. File includes draft content, rationale, and plan step reference
  3. External action is NOT executed immediately (no MCP call)
"""

import re
from pathlib import Path

import pytest
import yaml

from agents.skills.managing_obsidian_vault.approval_manager import (
    ApprovalManager,
    ApprovalRequest,
    ApprovalStatus,
)


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """Create a minimal vault structure."""
    (tmp_path / "Pending_Approval").mkdir()
    (tmp_path / "Approved").mkdir()
    (tmp_path / "Rejected").mkdir()
    (tmp_path / "Done" / "Actions").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def manager(vault: Path) -> ApprovalManager:
    return ApprovalManager(vault_root=vault)


# ---------------------------------------------------------------------------
# Test 1: File created in /Pending_Approval/ with correct name format
# ---------------------------------------------------------------------------

def test_approval_file_created_in_pending_folder(manager: ApprovalManager, vault: Path):
    """Approval file should land in /Pending_Approval/ with ISO timestamp prefix."""
    file_path = manager.draft_external_action(
        action_type="email",
        target_recipient="client@example.com",
        plan_id="PLAN-2026-001",
        step_id=4,
        draft_content="Dear Client, please find your invoice attached.",
        rationale="Step 4 requires sending invoice to Client A.",
    )

    # File exists in the right folder
    assert file_path.parent == vault / "Pending_Approval"
    assert file_path.exists()

    # Filename matches expected pattern: <ISO-timestamp>_email_<slug>.md
    name_pattern = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z_email_[a-z0-9\-]+\.md$"
    )
    assert name_pattern.match(file_path.name), (
        f"Filename '{file_path.name}' does not match expected pattern"
    )


# ---------------------------------------------------------------------------
# Test 2: File content has all required metadata fields
# ---------------------------------------------------------------------------

def test_approval_file_contains_required_metadata(manager: ApprovalManager, vault: Path):
    """Approval file YAML must include action_type, target_recipient, plan_id, step_id, rationale."""
    file_path = manager.draft_external_action(
        action_type="email",
        target_recipient="client@example.com",
        plan_id="PLAN-2026-001",
        step_id=4,
        draft_content="Dear Client, please find your invoice attached.",
        rationale="Step 4 requires sending invoice to Client A.",
    )

    req = ApprovalRequest.from_file(file_path)

    assert req.action_type == "email"
    assert req.target_recipient == "client@example.com"
    assert req.plan_id == "PLAN-2026-001"
    assert req.step_id == 4
    assert "invoice" in req.rationale.lower()
    assert req.status == ApprovalStatus.PENDING


# ---------------------------------------------------------------------------
# Test 3: Draft content is preserved verbatim in the file body
# ---------------------------------------------------------------------------

def test_approval_file_preserves_draft_content(manager: ApprovalManager, vault: Path):
    """Full draft content must appear in the file body."""
    draft = "Dear Client A,\n\nPlease find Invoice #2026-001 attached.\n\nKind regards."

    file_path = manager.draft_external_action(
        action_type="email",
        target_recipient="client@example.com",
        plan_id="PLAN-2026-001",
        step_id=4,
        draft_content=draft,
        rationale="Invoice delivery step.",
    )

    raw_content = file_path.read_text(encoding="utf-8")
    assert "Dear Client A," in raw_content
    assert "Invoice #2026-001" in raw_content


# ---------------------------------------------------------------------------
# Test 4: Human instruction text is present
# ---------------------------------------------------------------------------

def test_approval_file_contains_human_instructions(manager: ApprovalManager, vault: Path):
    """File must tell the human to move it to /Approved/ or /Rejected/."""
    file_path = manager.draft_external_action(
        action_type="email",
        target_recipient="client@example.com",
        plan_id="PLAN-2026-001",
        step_id=4,
        draft_content="Invoice body.",
        rationale="Send invoice.",
    )

    raw_content = file_path.read_text(encoding="utf-8")
    assert "/Approved/" in raw_content
    assert "/Rejected/" in raw_content


# ---------------------------------------------------------------------------
# Test 5: External action NOT executed immediately (no MCP side-effects)
# ---------------------------------------------------------------------------

def test_no_execution_on_draft(manager: ApprovalManager, vault: Path):
    """After drafting, the /Approved/ and /Done/Actions/ folders must remain empty."""
    manager.draft_external_action(
        action_type="email",
        target_recipient="client@example.com",
        plan_id="PLAN-2026-001",
        step_id=4,
        draft_content="Invoice body.",
        rationale="Send invoice.",
    )

    # Nothing in /Approved/ or /Done/Actions/
    approved_files = list((vault / "Approved").glob("*.md"))
    done_files = list((vault / "Done" / "Actions").glob("*.md"))

    assert len(approved_files) == 0, "Action should NOT be executed immediately"
    assert len(done_files) == 0, "Action should NOT be archived immediately"


# ---------------------------------------------------------------------------
# Test 6: Invalid action_type raises ValueError
# ---------------------------------------------------------------------------

def test_invalid_action_type_raises(manager: ApprovalManager):
    with pytest.raises(ValueError, match="Invalid action_type"):
        manager.draft_external_action(
            action_type="fax",           # not in valid set
            target_recipient="foo@bar.com",
            plan_id="PLAN-001",
            step_id=1,
            draft_content="content",
            rationale="reason",
        )
