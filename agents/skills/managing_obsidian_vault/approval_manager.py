"""
ApprovalManager: HITL (Human-in-the-Loop) approval workflow for Silver Tier.

Manages the lifecycle of external-action approval files:
  /Pending_Approval/ → /Approved/ → /Done/Actions/
                     → /Rejected/

All external actions (email, payment, social post, API call) MUST be drafted
here before execution. No MCP call proceeds without a corresponding approval file
in /Approved/.

Classes:
    ApprovalStatus: Enum of possible file states
    ApprovalRequest: Parsed approval request metadata
    ApprovalManager: Core workflow manager

Functions exposed via ApprovalManager:
    draft_external_action()    — Create approval request in /Pending_Approval/
    detect_approval_status()   — Check current state of an approval file
    execute_approved_action()  — Dispatch MCP call for an approved file
    reject_action()            — Log rejection, update plan reasoning
    scan_pending_approvals()   — List all pending files for a given plan
"""

import logging
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


@dataclass
class ApprovalRequest:
    """Parsed approval request file."""
    action_type: str                  # email | payment | social_post | api_call | other
    target_recipient: str
    plan_id: str
    step_id: int
    rationale: str
    draft_content: str
    created_date: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    execution_result: Optional[str] = None
    file_path: Optional[Path] = None

    @classmethod
    def from_file(cls, path: Path) -> "ApprovalRequest":
        """Parse an approval request markdown file."""
        raw = path.read_text(encoding="utf-8")

        # Split YAML frontmatter from body
        if not raw.startswith("---"):
            raise ValueError(f"Missing YAML frontmatter in {path}")

        parts = raw.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"Malformed YAML frontmatter in {path}")

        try:
            meta = yaml.safe_load(parts[1])
        except yaml.YAMLError as exc:
            raise ValueError(f"Corrupted YAML in {path}: {exc}") from exc

        if meta is None:
            raise ValueError(f"Empty YAML frontmatter in {path}")

        required_fields = ["action_type", "target_recipient", "plan_id", "step_id",
                           "rationale", "created_date", "status"]
        for field_name in required_fields:
            if field_name not in meta:
                raise ValueError(f"Missing required field '{field_name}' in {path}")

        return cls(
            action_type=str(meta["action_type"]),
            target_recipient=str(meta["target_recipient"]),
            plan_id=str(meta["plan_id"]),
            step_id=int(meta["step_id"]),
            rationale=str(meta["rationale"]),
            created_date=str(meta["created_date"]),
            status=ApprovalStatus(meta["status"]),
            draft_content=parts[2].strip(),
            execution_result=meta.get("execution_result"),
            file_path=path,
        )

    def to_yaml_block(self) -> str:
        """Render YAML frontmatter block."""
        data: dict = {
            "action_type": self.action_type,
            "target_recipient": self.target_recipient,
            "plan_id": self.plan_id,
            "step_id": self.step_id,
            "rationale": self.rationale,
            "created_date": self.created_date,
            "status": self.status.value,
        }
        if self.execution_result is not None:
            data["execution_result"] = self.execution_result
        return yaml.dump(data, default_flow_style=False, allow_unicode=True).strip()

    def render_file_content(self) -> str:
        """Render complete file content (frontmatter + body)."""
        yaml_block = self.to_yaml_block()
        return f"---\n{yaml_block}\n---\n\n{self.draft_content}\n"


# ---------------------------------------------------------------------------
# ApprovalManager
# ---------------------------------------------------------------------------

class ApprovalManager:
    """
    Manages the HITL approval lifecycle for Silver Tier external actions.

    Vault folder layout expected:
        <vault_root>/Pending_Approval/
        <vault_root>/Approved/
        <vault_root>/Rejected/
        <vault_root>/Done/Actions/
    """

    def __init__(self, vault_root: Path) -> None:
        self.vault_root = vault_root
        self.pending_dir = vault_root / "Pending_Approval"
        self.approved_dir = vault_root / "Approved"
        self.rejected_dir = vault_root / "Rejected"
        self.done_dir = vault_root / "Done" / "Actions"

        logger.info("ApprovalManager initialised with vault_root=%s", vault_root)

    # ------------------------------------------------------------------
    # T036 — DraftExternalAction
    # ------------------------------------------------------------------

    def draft_external_action(
        self,
        action_type: str,
        target_recipient: str,
        plan_id: str,
        step_id: int,
        draft_content: str,
        rationale: str,
    ) -> Path:
        """
        Create an approval request file in /Pending_Approval/.

        The agent MUST call this instead of directly invoking an MCP server.
        Execution is blocked until the file is moved to /Approved/.

        Args:
            action_type: email | payment | social_post | api_call | other
            target_recipient: Email address, account handle, or endpoint
            plan_id: Containing plan identifier
            step_id: Step number within the plan (1-indexed)
            draft_content: Full content to be executed (email body, etc.)
            rationale: Why this action is needed (plan context)

        Returns:
            Path to created approval request file

        Raises:
            ValueError: If required inputs are missing or action_type invalid
            IOError: If file creation fails
        """
        valid_types = {"email", "payment", "social_post", "api_call", "other"}
        if action_type not in valid_types:
            raise ValueError(
                f"Invalid action_type '{action_type}'. Must be one of: {valid_types}"
            )
        if not target_recipient:
            raise ValueError("target_recipient is required")
        if not draft_content:
            raise ValueError("draft_content is required")

        timestamp = self._iso_timestamp()
        slug = self._slugify(target_recipient)
        filename = f"{timestamp.replace(':', '-')}_{action_type}_{slug}.md"

        request = ApprovalRequest(
            action_type=action_type,
            target_recipient=target_recipient,
            plan_id=plan_id,
            step_id=step_id,
            rationale=rationale,
            draft_content=self._build_draft_body(action_type, target_recipient, draft_content),
            created_date=timestamp,
            status=ApprovalStatus.PENDING,
        )

        file_path = self.pending_dir / filename
        self._atomic_write(file_path, request.render_file_content())
        request.file_path = file_path

        logger.info(
            "Approval request drafted: %s (plan=%s, step=%d)",
            file_path.name, plan_id, step_id,
        )
        return file_path

    # ------------------------------------------------------------------
    # T038 — detect_approval_status
    # ------------------------------------------------------------------

    def detect_approval_status(self, filename: str) -> ApprovalStatus:
        """
        Determine the current approval state of a request by scanning folders.

        Args:
            filename: Bare filename (e.g. '2026-02-24T10-00-00Z_email_foo.md')

        Returns:
            ApprovalStatus indicating where the file currently lives
        """
        if (self.approved_dir / filename).exists():
            return ApprovalStatus.APPROVED
        if (self.rejected_dir / filename).exists():
            return ApprovalStatus.REJECTED
        if (self.done_dir / filename).exists():
            return ApprovalStatus.EXECUTED
        if (self.pending_dir / filename).exists():
            return ApprovalStatus.PENDING

        raise FileNotFoundError(
            f"Approval file '{filename}' not found in any approval folder"
        )

    def scan_pending_approvals(self, plan_id: Optional[str] = None) -> list[ApprovalRequest]:
        """
        Return all pending approval requests, optionally filtered by plan.

        Args:
            plan_id: If provided, return only requests for this plan

        Returns:
            List of parsed ApprovalRequest objects
        """
        if not self.pending_dir.exists():
            return []

        requests: list[ApprovalRequest] = []
        for path in sorted(self.pending_dir.glob("*.md")):
            try:
                req = ApprovalRequest.from_file(path)
                if plan_id is None or req.plan_id == plan_id:
                    requests.append(req)
            except (ValueError, KeyError) as exc:
                logger.warning("Skipping malformed approval file %s: %s", path.name, exc)

        return requests

    # ------------------------------------------------------------------
    # T039 — execute_approved_action
    # ------------------------------------------------------------------

    def execute_approved_action(
        self,
        filename: str,
        mcp_dispatcher: Optional[object] = None,
    ) -> tuple[bool, str]:
        """
        Execute an approved external action via MCP dispatcher.

        Process:
          1. Re-read file from /Approved/ to confirm status
          2. Parse action_type and content
          3. Call mcp_dispatcher (if provided); otherwise simulate/log
          4. On success: move file to /Done/Actions/, update status
          5. On failure: move file back to /Pending_Approval/ with error

        Args:
            filename: Approval filename to execute
            mcp_dispatcher: Optional callable that receives ApprovalRequest.
                            If None, execution is simulated (dry-run mode).

        Returns:
            (success: bool, message: str)
        """
        approved_path = self.approved_dir / filename
        if not approved_path.exists():
            raise FileNotFoundError(f"Approved file not found: {approved_path}")

        try:
            req = ApprovalRequest.from_file(approved_path)
        except ValueError as exc:
            raise ValueError(f"Cannot parse approved file: {exc}") from exc

        if req.status not in (ApprovalStatus.APPROVED, ApprovalStatus.PENDING):
            logger.warning(
                "File %s has unexpected status %s; proceeding with execution",
                filename, req.status,
            )

        # Attempt execution
        try:
            if mcp_dispatcher is not None:
                result_msg = mcp_dispatcher(req)
            else:
                # Dry-run: log and simulate success
                result_msg = (
                    f"[DRY-RUN] Would execute {req.action_type} → {req.target_recipient}"
                )
                logger.info(result_msg)

            # Success: update status and move to /Done/Actions/
            req.status = ApprovalStatus.EXECUTED
            req.execution_result = result_msg
            dest = self.done_dir / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            self._atomic_write(dest, req.render_file_content())
            approved_path.unlink(missing_ok=True)

            logger.info("Action executed and archived: %s", filename)
            return True, result_msg

        except Exception as exc:  # noqa: BLE001
            error_msg = f"MCP execution failed: {exc}"
            logger.error(error_msg)

            # Failure: annotate and move back to /Pending_Approval/
            req.execution_result = error_msg
            recovery_path = self.pending_dir / filename
            self._atomic_write(recovery_path, req.render_file_content())
            approved_path.unlink(missing_ok=True)

            return False, error_msg

    # ------------------------------------------------------------------
    # Rejection handling
    # ------------------------------------------------------------------

    def record_rejection(self, filename: str) -> ApprovalRequest:
        """
        Read a file from /Rejected/ and return the parsed request for audit logging.

        Args:
            filename: Approval filename in /Rejected/

        Returns:
            Parsed ApprovalRequest with status=rejected
        """
        rejected_path = self.rejected_dir / filename
        if not rejected_path.exists():
            raise FileNotFoundError(f"Rejected file not found: {rejected_path}")

        req = ApprovalRequest.from_file(rejected_path)
        req.status = ApprovalStatus.REJECTED
        self._atomic_write(rejected_path, req.render_file_content())

        logger.info(
            "Rejection recorded for %s (plan=%s, step=%d)",
            filename, req.plan_id, req.step_id,
        )
        return req

    # ------------------------------------------------------------------
    # T044 — validate_hitl_completion (called from PlanManager)
    # ------------------------------------------------------------------

    def validate_hitl_step_has_approval(
        self,
        plan_id: str,
        step_id: int,
    ) -> bool:
        """
        Verify that a HITL step has a corresponding executed approval file.

        A ✋ step may not be marked [x] without proof that its external action
        was approved and executed.

        Args:
            plan_id: Plan identifier
            step_id: Step number

        Returns:
            True if executed approval file exists for this plan+step

        Raises:
            PermissionError: If no executed approval found (blocks step completion)
        """
        for folder in (self.done_dir, self.approved_dir):
            if not folder.exists():
                continue
            for path in folder.glob("*.md"):
                try:
                    req = ApprovalRequest.from_file(path)
                    if req.plan_id == plan_id and req.step_id == step_id:
                        logger.info(
                            "HITL approval verified for plan=%s step=%d: %s",
                            plan_id, step_id, path.name,
                        )
                        return True
                except (ValueError, KeyError):
                    continue

        raise PermissionError(
            f"Cannot mark step {step_id} complete for plan {plan_id}: "
            f"no executed approval file found. "
            f"HITL steps require an approved action in /Done/Actions/ or /Approved/."
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write content atomically using temp-file-and-rename pattern."""
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.parent / f".{path.name}.tmp"
        try:
            temp_path.write_text(content, encoding="utf-8")
            temp_path.replace(path)
            logger.debug("Atomic write complete: %s", path)
        except OSError as exc:
            temp_path.unlink(missing_ok=True)
            raise IOError(f"Atomic write failed for {path}: {exc}") from exc

    @staticmethod
    def _iso_timestamp() -> str:
        """Return current UTC time as ISO-8601 string."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to lowercase slug (alphanumeric + hyphens)."""
        text = text.lower()
        text = re.sub(r"[^a-z0-9]+", "-", text)
        return text.strip("-")[:40]

    @staticmethod
    def _build_draft_body(action_type: str, target_recipient: str, draft_content: str) -> str:
        """Wrap draft content with human-readable instructions."""
        return (
            f"# {action_type.replace('_', ' ').title()} Approval Request\n\n"
            f"**To / Target**: {target_recipient}\n\n"
            f"---\n\n"
            f"## Draft Content\n\n"
            f"{draft_content}\n\n"
            f"---\n\n"
            f"> **Instructions for Human Review**:\n"
            f"> - Move this file to `/Approved/` to **execute** the action above.\n"
            f"> - Move this file to `/Rejected/` to **deny** the action.\n"
            f"> - Leave in `/Pending_Approval/` to keep the plan blocked.\n"
        )
