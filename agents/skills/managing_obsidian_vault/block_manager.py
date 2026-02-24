"""
BlockManager: Block detection and resolution for Silver Tier reasoning plans.

Manages the lifecycle of plan blocks caused by pending HITL approval requests:

  Detect block  → Set plan status = "Blocked", populate blocked_reason
  Monitor       → Track how long each plan has been blocked
  Resolve block → Move approval to /Approved/, restore plan to "Active", resume

This module integrates with:
  - PlanManager:     read/write plan metadata and reasoning logs
  - ApprovalManager: scan /Pending_Approval/ and /Approved/ for files

Classes:
    BlockInfo:    Snapshot of a single block (plan + approval file + age)
    BlockManager: Core detection and resolution logic

Functions exposed via BlockManager:
    detect_blocks()          — Scan vault; set Blocked status on affected plans
    resolve_block()          — Process approved file; restore Active status
    get_block_info()         — Return BlockInfo for a given plan (or None)
    is_stale_block()         — True if block older than threshold_hours
    scan_all_blocks()        — Return BlockInfo list for entire vault
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from agents.skills.managing_obsidian_vault.approval_manager import ApprovalManager, ApprovalStatus
from agents.skills.managing_obsidian_vault.plan_manager import PlanManager

logger = logging.getLogger(__name__)

DEFAULT_STALE_HOURS = 24


@dataclass
class BlockInfo:
    """Snapshot of a single plan block."""
    plan_id: str
    blocked_reason: str
    pending_filename: str          # File currently in /Pending_Approval/
    block_started_at: str          # ISO-8601 timestamp from approval file
    step_id: int
    step_description: str
    hours_blocked: float

    @property
    def is_stale(self) -> bool:
        return self.hours_blocked >= DEFAULT_STALE_HOURS

    @property
    def human_age(self) -> str:
        h = int(self.hours_blocked)
        m = int((self.hours_blocked - h) * 60)
        if h == 0:
            return f"{m}m"
        return f"{h}h {m}m"


class BlockManager:
    """
    Detects and resolves plan blocks caused by pending HITL approvals.

    Vault layout required:
        <vault_root>/Plans/
        <vault_root>/Pending_Approval/
        <vault_root>/Approved/
    """

    def __init__(self, vault_root: Path) -> None:
        self.vault_root = vault_root
        self.plan_manager = PlanManager(vault_root=vault_root)
        self.approval_manager = ApprovalManager(vault_root=vault_root)
        self.pending_dir = vault_root / "Pending_Approval"
        self.approved_dir = vault_root / "Approved"
        logger.info("BlockManager initialised with vault_root=%s", vault_root)

    # ------------------------------------------------------------------
    # T052 — detect_blocks
    # ------------------------------------------------------------------

    def detect_blocks(self, plan_id: Optional[str] = None) -> list[BlockInfo]:
        """
        Scan /Pending_Approval/ and update plan statuses accordingly.

        For each plan that has pending approval files:
          - Set plan.metadata.status = "Blocked"
          - Set plan.metadata.blocked_reason = "Approval request: <file> waiting since <time>"
          - Append Reasoning Log entry

        For plans that were Blocked but have no more pending approvals:
          - Restore plan.metadata.status = "Active"
          - Clear plan.metadata.blocked_reason

        Args:
            plan_id: If provided, only check this plan. Otherwise check all plans.

        Returns:
            List of BlockInfo for all currently blocked plans.
        """
        blocks: list[BlockInfo] = []

        plans_dir = self.vault_root / "Plans"
        if not plans_dir.exists():
            return blocks

        plan_files = (
            [plans_dir / f"PLAN-{plan_id}.md"]
            if plan_id
            else list(plans_dir.glob("PLAN-*.md"))
        )

        for plan_file in plan_files:
            if not plan_file.exists():
                continue
            try:
                self._check_plan_for_blocks(plan_file.stem, blocks)
            except (ValueError, FileNotFoundError) as exc:
                logger.warning("Skipping plan %s during block scan: %s", plan_file.name, exc)

        return blocks

    def _check_plan_for_blocks(self, plan_stem: str, blocks: list[BlockInfo]) -> None:
        """Check one plan file and update its blocked/active status."""
        plan = self.plan_manager.load_plan(plan_stem)
        if plan.metadata.status == "Done":
            return

        # Find pending approval files for this plan
        plan_id_variants = {
            plan.metadata.task_id,
            f"PLAN-{plan.metadata.task_id}",
        }
        pending_files = self._find_pending_for_plan(plan_id_variants)

        if pending_files:
            # Block the plan
            filename, req = pending_files[0]  # Use earliest pending file
            step_desc = self._get_step_description(plan, req.step_id)
            age_hours = self._hours_since(req.created_date)

            reason = (
                f"Approval request '{filename}' waiting since {req.created_date} "
                f"({age_hours:.1f}h) — Step {req.step_id}: {step_desc}"
            )

            changed = (
                plan.metadata.status != "Blocked"
                or plan.metadata.blocked_reason != reason
            )

            plan.metadata.status = "Blocked"
            plan.metadata.blocked_reason = reason

            if changed:
                plan.reasoning_logs.append(
                    f"[{self._iso_now()}] Agent: Plan blocked at step {req.step_id} "
                    f"— awaiting {req.action_type} approval: {filename}"
                )
                plan_path = self.plan_manager.plans_dir / f"PLAN-{plan.metadata.task_id}.md"
                self.plan_manager._write_plan_file(plan_path, plan)
                logger.info("Plan %s marked Blocked (approval: %s)", plan.metadata.task_id, filename)

            blocks.append(BlockInfo(
                plan_id=plan.metadata.task_id,
                blocked_reason=reason,
                pending_filename=filename,
                block_started_at=req.created_date,
                step_id=req.step_id,
                step_description=step_desc,
                hours_blocked=age_hours,
            ))

        elif plan.metadata.status == "Blocked":
            # No pending files left — clear the block
            self._clear_block(plan)

    def _find_pending_for_plan(
        self, plan_id_variants: set[str]
    ) -> list[tuple[str, object]]:
        """Return list of (filename, ApprovalRequest) for plan's pending files."""
        if not self.pending_dir.exists():
            return []

        results = []
        for path in sorted(self.pending_dir.glob("*.md")):
            try:
                from agents.skills.managing_obsidian_vault.approval_manager import ApprovalRequest
                req = ApprovalRequest.from_file(path)
                if req.plan_id in plan_id_variants:
                    results.append((path.name, req))
            except (ValueError, KeyError) as exc:
                logger.debug("Skipping malformed pending file %s: %s", path.name, exc)
        return results

    def _clear_block(self, plan) -> None:
        """Remove block status from a plan that has no more pending approvals."""
        plan.metadata.status = "Active"
        plan.metadata.blocked_reason = None
        plan.reasoning_logs.append(
            f"[{self._iso_now()}] Agent: Block cleared — no pending approvals remain. "
            f"Resuming plan {plan.metadata.task_id}."
        )
        plan_path = self.plan_manager.plans_dir / f"PLAN-{plan.metadata.task_id}.md"
        self.plan_manager._write_plan_file(plan_path, plan)
        logger.info("Plan %s unblocked (no pending approvals)", plan.metadata.task_id)

    # ------------------------------------------------------------------
    # T055 — resolve_block
    # ------------------------------------------------------------------

    def resolve_block(self, approval_filename: str) -> Optional[str]:
        """
        Process a file that has been moved to /Approved/.

        Steps:
          1. Parse approval file to get plan_id + step_id
          2. Re-run detect_blocks on the plan
          3. If no more pending approvals: plan restored to "Active"
          4. Return the next incomplete step description (for agent display)

        Args:
            approval_filename: Filename in /Approved/ (not full path)

        Returns:
            Next step description if plan can resume, else None
        """
        approved_path = self.approved_dir / approval_filename
        if not approved_path.exists():
            raise FileNotFoundError(f"Approved file not found: {approved_path}")

        from agents.skills.managing_obsidian_vault.approval_manager import ApprovalRequest
        try:
            req = ApprovalRequest.from_file(approved_path)
        except ValueError as exc:
            raise ValueError(f"Cannot parse approved file: {exc}") from exc

        # Re-scan blocks for this plan — if no pending files remain, it unblocks
        plan_id = req.plan_id
        if not plan_id.startswith("PLAN-"):
            plan_id_stem = plan_id
        else:
            plan_id_stem = plan_id[len("PLAN-"):]

        remaining_blocks = self.detect_blocks(plan_id=plan_id_stem)

        if not remaining_blocks:
            # Plan is now unblocked
            try:
                plan = self.plan_manager.load_plan(plan_id_stem)
                next_step = plan.get_next_incomplete_step()
                next_desc = next_step.description if next_step else "All steps complete"
                logger.info(
                    "Block resolved for plan %s; next step: %s", plan_id_stem, next_desc
                )
                return next_desc
            except (ValueError, FileNotFoundError):
                return None

        logger.info(
            "Plan %s still has %d pending approval(s)", plan_id_stem, len(remaining_blocks)
        )
        return None

    # ------------------------------------------------------------------
    # T054 — stale block helpers (used by DashboardReconciler)
    # ------------------------------------------------------------------

    def is_stale_block(self, block: BlockInfo, threshold_hours: int = DEFAULT_STALE_HOURS) -> bool:
        """Return True if the block has been waiting longer than threshold_hours."""
        return block.hours_blocked >= threshold_hours

    def scan_all_blocks(self) -> list[BlockInfo]:
        """Return BlockInfo for every currently blocked plan in the vault."""
        return self.detect_blocks()

    def get_block_info(self, plan_id: str) -> Optional[BlockInfo]:
        """Return BlockInfo for a specific plan, or None if not blocked."""
        blocks = self.detect_blocks(plan_id=plan_id)
        return blocks[0] if blocks else None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_step_description(plan, step_id: int) -> str:
        """Return description of step at step_id (1-indexed), or fallback string."""
        if 1 <= step_id <= len(plan.steps):
            return plan.steps[step_id - 1].description
        return f"step {step_id}"

    @staticmethod
    def _hours_since(iso_timestamp: str) -> float:
        """Return hours elapsed since the given ISO-8601 timestamp."""
        try:
            then = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
            delta = datetime.now(timezone.utc) - then
            return delta.total_seconds() / 3600
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _iso_now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
